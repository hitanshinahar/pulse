import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models import RecoveryExecution, RecoveryOutcome, FinancialObligation, RazorpayEvent

logger = logging.getLogger(__name__)

async def attribute_payment_to_recovery(db: AsyncSession, event: RazorpayEvent, obligation: FinancialObligation):
    """
    Consumes processed financial events and attributes them to recovery actions if applicable.
    Distinguishes between ORGANIC payments and RECOVERY_ATTRIBUTED payments.
    Called *after* the FinancialStateEngine has updated authoritative financial state.
    """
    payload = event.parsed_payload
    
    # We primarily look for payment_link.paid which has the explicit reference_id
    if event.event_type != "payment_link.paid":
        # For standard payment.captured, it might just be an organic payment
        # We can still record an ORGANIC outcome if it satisfies the obligation but has no recovery link
        return

    try:
        plink_entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        reference_id = plink_entity.get("reference_id")
        
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        payment_id = payment_entity.get("id")
        amount_paid_paise = payment_entity.get("amount", 0)
        amount_paid = Decimal(str(amount_paid_paise)) / Decimal('100')
        
    except Exception as e:
        logger.error(f"Failed to parse payment_link.paid payload for attribution: {e}")
        return

    if not reference_id:
        logger.info(f"Event {event.id} lacks reference_id, treating as organic (no attribution).")
        return

    # Look for matching RecoveryExecution
    stmt = select(RecoveryExecution).where(RecoveryExecution.razorpay_reference_id == reference_id)
    execution = (await db.execute(stmt)).scalar_one_or_none()
    
    if not execution:
        logger.info(f"Event {event.id} reference {reference_id} does not map to any execution. Organic.")
        return

    # We found the execution. Calculate outcome
    time_to_recovery = None
    if execution.executed_at:
        delta = datetime.now(timezone.utc) - execution.executed_at
        time_to_recovery = int(delta.total_seconds())

    # Determine outcome based on obligation's current authoritative state
    if obligation.outstanding_amount <= Decimal('0.00'):
        outcome_status = "RECOVERED"
    else:
        outcome_status = "PARTIALLY_RECOVERED"

    # Create RecoveryOutcome
    outcome = RecoveryOutcome(
        execution_id=execution.id,
        obligation_id=obligation.id,
        payment_id=payment_id,
        amount_recovered=amount_paid,
        recovered_at=datetime.now(timezone.utc),
        time_to_recovery_seconds=time_to_recovery,
        outcome=outcome_status,
        evidence_event_id=event.id,
        attribution_type="RECOVERY_ATTRIBUTED"
    )
    db.add(outcome)
    
    # Update execution status to reflect successful attribution
    execution.execution_status = outcome_status
    
    logger.info(f"Successfully attributed payment {payment_id} to execution {execution.id} ({outcome_status})")
    return outcome
