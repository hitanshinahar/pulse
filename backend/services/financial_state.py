import logging
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from backend.models import (
    RazorpayEvent,
    FinancialObligation,
    PaymentAttempt,
    ObligationStateTransition
)
from backend.integrations.razorpay.client import get_razorpay_client

logger = logging.getLogger(__name__)

def parse_currency_amount(amount_in_smallest_unit: int) -> Decimal:
    """Razorpay amounts are in smallest unit (e.g. paise). Convert to decimal representation."""
    return Decimal(amount_in_smallest_unit) / Decimal(100)

async def reconcile_order_with_razorpay(order_id: str) -> Optional[Dict[str, Any]]:
    """Fetch authoritative order state from Razorpay."""
    try:
        client = get_razorpay_client()
        # The razorpay client is synchronous, so we run it in a threadpool
        import asyncio
        loop = asyncio.get_event_loop()
        order = await loop.run_in_executor(None, client.order.fetch, order_id)
        return order
    except Exception as e:
        logger.error(f"Failed to fetch order {order_id} from Razorpay: {e}")
        return None

async def reconcile_payment_with_razorpay(payment_id: str) -> Optional[Dict[str, Any]]:
    """Fetch authoritative payment state from Razorpay."""
    try:
        client = get_razorpay_client()
        import asyncio
        loop = asyncio.get_event_loop()
        payment = await loop.run_in_executor(None, client.payment.fetch, payment_id)
        return payment
    except Exception as e:
        logger.error(f"Failed to fetch payment {payment_id} from Razorpay: {e}")
        return None

async def _get_or_create_obligation(
    db: AsyncSession, 
    order_id: str, 
    api_order_data: Optional[Dict[str, Any]] = None
) -> Tuple[FinancialObligation, bool]:
    """
    Gets existing obligation or creates one using Razorpay API data.
    Returns (obligation, created)
    """
    stmt = select(FinancialObligation).where(FinancialObligation.razorpay_order_id == order_id).with_for_update()
    result = await db.execute(stmt)
    obligation = result.scalar_one_or_none()

    if obligation:
        return obligation, False
        
    if not api_order_data:
        # We MUST reconcile if we don't have order data.
        api_order_data = await reconcile_order_with_razorpay(order_id)
        if not api_order_data:
            raise ValueError(f"Cannot safely create obligation for order {order_id} without Razorpay API data.")

    # Create obligation
    amount = parse_currency_amount(api_order_data.get('amount', 0))
    receipt = api_order_data.get('receipt') # Optional merchant reference
    currency = api_order_data.get('currency', 'INR')

    obligation = FinancialObligation(
        razorpay_order_id=order_id,
        merchant_reference=receipt,
        amount=amount,
        currency=currency,
        satisfied_amount=Decimal(0),
        outstanding_amount=amount,
        status="UNRESOLVED",
        state_version=1
    )
    db.add(obligation)
    await db.flush() # Ensure it gets an ID
    return obligation, True

async def process_razorpay_event(db: AsyncSession, event_id: str):
    """
    Process a single RazorpayEvent deterministically.
    This must be called within a database transaction context if you want atomicity, 
    but we will handle the transaction block here.
    """
    async with db.begin():
        stmt = select(RazorpayEvent).where(
            RazorpayEvent.id == event_id,
            RazorpayEvent.status == "RECEIVED"
        ).with_for_update()
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            # Event might be already processed or doesn't exist
            return
        
        try:
            await _process_event_logic(db, event)
            event.status = "PROCESSED"
        except ValueError as e:
            # Domain error (e.g. ambiguity)
            event.status = "FAILED"
            event.error_msg = str(e)
            logger.warning(f"Domain error processing event {event.razorpay_event_id}: {e}")
        except Exception as e:
            # Unexpected error
            event.status = "FAILED"
            event.error_msg = str(e)
            logger.exception(f"Unexpected error processing event {event.razorpay_event_id}")

async def _process_event_logic(db: AsyncSession, event: RazorpayEvent):
    payload = event.parsed_payload
    
    if not isinstance(payload, dict):
        raise ValueError("Payload is not a valid JSON object.")
    
    payload_body = payload.get('payload', {})
    
    # We mainly care about payment events for this MVP
    payment_entity = payload_body.get('payment', {}).get('entity', {})
    order_entity = payload_body.get('order', {}).get('entity', {})

    payment_id = payment_entity.get('id')
    order_id = payment_entity.get('order_id') or order_entity.get('id')
    
    if not order_id:
        raise ValueError("Event does not contain a Razorpay Order ID. Cannot project financial state.")
        
    # Safely get or create obligation
    obligation, created = await _get_or_create_obligation(db, order_id)
    
    prev_status = obligation.status
    prev_version = obligation.state_version
    state_changed = False
    
    if payment_id:
        # Handle payment attempt updates
        payment_amount = parse_currency_amount(payment_entity.get('amount', 0))
        payment_currency = payment_entity.get('currency', 'INR')
        payment_status = payment_entity.get('status', 'created')
        
        # Check for existing payment attempt
        stmt = select(PaymentAttempt).where(PaymentAttempt.razorpay_payment_id == payment_id).with_for_update()
        result = await db.execute(stmt)
        payment_attempt = result.scalar_one_or_none()
        
        payment_status_changed = False
        
        if payment_attempt:
            if payment_attempt.razorpay_status != payment_status:
                payment_attempt.razorpay_status = payment_status
                payment_status_changed = True
        else:
            payment_attempt = PaymentAttempt(
                razorpay_payment_id=payment_id,
                razorpay_order_id=order_id,
                obligation_id=obligation.id,
                amount=payment_amount,
                currency=payment_currency,
                payment_method=payment_entity.get('method'),
                razorpay_status=payment_status
            )
            db.add(payment_attempt)
            payment_status_changed = True
            
        await db.flush()
            
        # If payment status changed, we need to recompute obligation financial state
        if payment_status_changed:
            # Recompute total satisfied amount directly from the authoritative attempts table
            stmt = select(PaymentAttempt).where(
                PaymentAttempt.obligation_id == obligation.id,
                PaymentAttempt.razorpay_status == 'captured'
            )
            result = await db.execute(stmt)
            captured_attempts = result.scalars().all()
            
            new_satisfied_amount = sum((a.amount for a in captured_attempts), Decimal(0))
            
            if obligation.satisfied_amount != new_satisfied_amount:
                obligation.satisfied_amount = new_satisfied_amount
                obligation.outstanding_amount = obligation.amount - new_satisfied_amount
                state_changed = True

    # State Machine Evaluation
    # States: UNRESOLVED, RECOVERY_ELIGIBLE, AMBIGUOUS, PARTIALLY_SATISFIED, SATISFIED, OVER_COLLECTED, ESCALATED, CLOSED
    new_status = obligation.status
    
    if obligation.outstanding_amount == 0 and obligation.satisfied_amount > 0:
        new_status = "SATISFIED"
    elif obligation.outstanding_amount < 0:
        new_status = "OVER_COLLECTED"
    elif obligation.outstanding_amount > 0 and obligation.satisfied_amount > 0:
        new_status = "PARTIALLY_SATISFIED"
    elif obligation.outstanding_amount == obligation.amount:
        # Has it failed?
        # Check if there are any failed attempts
        stmt = select(PaymentAttempt).where(
            PaymentAttempt.obligation_id == obligation.id,
            PaymentAttempt.razorpay_status == 'failed'
        )
        result = await db.execute(stmt)
        failed_attempts = result.scalars().all()
        
        if len(failed_attempts) > 0:
            new_status = "RECOVERY_ELIGIBLE"
        else:
            new_status = "UNRESOLVED"
            
    if new_status != prev_status:
        obligation.status = new_status
        state_changed = True

    if state_changed or created:
        obligation.state_version += 1
        
        # Record state transition
        transition = ObligationStateTransition(
            obligation_id=obligation.id,
            previous_state=prev_status if not created else "NONE",
            new_state=obligation.status,
            previous_version=prev_version if not created else 0,
            new_version=obligation.state_version,
            triggering_event_id=event.id,
            reason=event.event_type,
            source="razorpay_webhook"
        )
        db.add(transition)

async def run_processor(db: AsyncSession, limit: int = 50):
    """
    Polls the RazorpayEvent table for RECEIVED events and processes them.
    Can be run as a background cron or script.
    """
    stmt = select(RazorpayEvent.id).where(
        RazorpayEvent.status == "RECEIVED"
    ).order_by(RazorpayEvent.created_at.asc()).limit(limit)
    
    result = await db.execute(stmt)
    event_ids = result.scalars().all()
    
    # Commit the transaction started by the SELECT so that process_razorpay_event can start its own
    await db.commit()
    
    processed_count = 0
    for event_id in event_ids:
        await process_razorpay_event(db, event_id)
        processed_count += 1
        
    return processed_count
