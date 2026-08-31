import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from razorpay.errors import BadRequestError, ServerError

from backend.models import (
    RecoveryExecution, 
    RecoveryDecision, 
    FinancialObligation, 
    RecoveryPolicy
)
from backend.integrations.razorpay.client import get_razorpay_client

logger = logging.getLogger(__name__)

async def execute_recovery(db: AsyncSession, execution_id: str) -> RecoveryExecution:
    """
    Executes an authorized recovery action, ensuring state is valid and TOCTOU protected.
    Creates a Razorpay Payment Link if constraints are met.
    """
    # 1. Load RecoveryExecution
    stmt = select(RecoveryExecution).where(RecoveryExecution.id == execution_id)
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Verify execution state
    if execution.execution_status not in ["AUTHORIZED_PENDING_EXECUTION", "AUTHORIZED"]:
        return execution

    # 2. Retrieve associated Decision & Obligation
    stmt = select(RecoveryDecision).where(RecoveryDecision.id == execution.decision_id)
    decision = (await db.execute(stmt)).scalar_one()

    stmt = select(FinancialObligation).where(FinancialObligation.id == execution.obligation_id)
    obligation = (await db.execute(stmt)).scalar_one()

    # 3. Dual TOCTOU Validation
    if obligation.state_version != decision.state_version:
        await _block_execution(db, execution, "EXECUTION_BLOCKED_STALE_STATE", "Obligation state version changed")
        return execution

    if obligation.outstanding_amount <= Decimal('0.00'):
        await _block_execution(db, execution, "EXECUTION_BLOCKED_SATISFIED", "Obligation has no outstanding balance")
        return execution

    if execution.action != "PAYMENT_LINK":
        await _block_execution(db, execution, "EXECUTION_BLOCKED_UNSUPPORTED_ACTION", f"Action {execution.action} not supported")
        return execution

    stmt = select(RecoveryPolicy).order_by(RecoveryPolicy.created_at.desc()).limit(1)
    policy = (await db.execute(stmt)).scalar_one_or_none()
    if not policy or not policy.enabled or execution.action not in policy.allowed_actions:
        await _block_execution(db, execution, "EXECUTION_BLOCKED_POLICY", "Policy disabled or action not allowed")
        return execution

    if obligation.currency != "INR":
        await _block_execution(db, execution, "EXECUTION_BLOCKED_CURRENCY", f"Unsupported currency {obligation.currency}. Only INR allowed.")
        return execution

    # Determine amount in smallest unit strictly via Decimal
    amount_in_paise = int(obligation.outstanding_amount * Decimal('100'))

    # Generate exact deterministic reference
    # UUID hex is 32 chars. PULSE-REC- is 10 chars. PULSE-REC-{hex} = 42 chars.
    # We must ensure length <= 40. We will use P-REC-{hex} (38 chars) or REC-{hex} (36 chars)
    # The prompt requested "PULSE-REC-{execution_id}". Let's truncate if necessary.
    raw_reference = f"PULSE-REC-{str(execution.id)}"
    razorpay_reference_id = raw_reference[:40]

    # Pre-persist reference_id and transition to EXECUTING
    execution.razorpay_reference_id = razorpay_reference_id
    execution.execution_status = "EXECUTING"
    await db.commit()
    await db.refresh(execution)

    # 4. External Execution
    try:
        client = get_razorpay_client()
        payload = {
            "amount": amount_in_paise,
            "currency": "INR",
            "reference_id": razorpay_reference_id,
            "description": f"Pulse Recovery",
            "reminder_enable": True
        }
        
        response = client.payment_link.create(payload)

        # Success
        execution.razorpay_payment_link_id = response.get('id')
        execution.short_url = response.get('short_url')
        execution.execution_status = "EXECUTED"
        execution.executed_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(execution)
        return execution

    except BadRequestError as e:
        logger.error(f"Razorpay 4xx error: {e}")
        execution.execution_status = "EXECUTION_FAILED"
        await db.commit()
        await db.refresh(execution)
        return execution
    except (ServerError, Exception) as e:
        logger.error(f"Razorpay ambiguous error: {e}")
        execution.execution_status = "EXECUTION_UNKNOWN"
        await db.commit()
        await db.refresh(execution)
        return execution


async def _block_execution(db: AsyncSession, execution: RecoveryExecution, status: str, reason: str):
    logger.warning(f"Execution {execution.id} blocked: {reason}")
    execution.execution_status = status
    await db.commit()
    await db.refresh(execution)
