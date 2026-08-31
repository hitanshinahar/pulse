import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models import RecoveryExecution

logger = logging.getLogger(__name__)

# Expiration threshold for an unknown execution (e.g., 48 hours)
UNKNOWN_EXPIRATION_HOURS = 48

async def reconcile_unknown_execution(db: AsyncSession, execution_id: str) -> RecoveryExecution:
    """
    Reconciles an EXECUTION_UNKNOWN state.
    Because Razorpay does not support filtering by reference_id natively via API,
    this method will simply enforce an expiration window. It does NOT query Razorpay.
    If the timeout has elapsed, it transitions the execution out of UNKNOWN to allow retries.
    Otherwise, it remains UNKNOWN, waiting for a definitive webhook.
    """
    stmt = select(RecoveryExecution).where(RecoveryExecution.id == execution_id)
    execution = (await db.execute(stmt)).scalar_one_or_none()
    
    if not execution:
        return None

    if execution.execution_status != "EXECUTION_UNKNOWN":
        return execution

    # Determine how long it has been in UNKNOWN state
    # Fallback to created_at if executed_at is None
    ref_time = execution.executed_at or execution.created_at
    now = datetime.now(timezone.utc)
    
    if now - ref_time > timedelta(hours=UNKNOWN_EXPIRATION_HOURS):
        # We safely assume the request either failed permanently or the link expired remotely
        logger.info(f"Execution {execution.id} exceeded UNKNOWN expiration threshold. Marking as NOT_RECOVERED.")
        execution.execution_status = "NOT_RECOVERED"
        await db.commit()
        await db.refresh(execution)
    else:
        logger.info(f"Execution {execution.id} remains in EXECUTION_UNKNOWN (awaiting webhook evidence).")

    return execution
