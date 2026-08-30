import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models import RazorpayEvent

logger = logging.getLogger(__name__)

async def process_razorpay_event(event_id: str, db: AsyncSession):
    """
    Decoupled processing logic for a Razorpay webhook event.
    This function expects the event to already be safely persisted in the database.
    """
    logger.info(f"Starting processing for event database ID: {event_id}")

    try:
        # Fetch the event from the DB
        stmt = select(RazorpayEvent).where(RazorpayEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            logger.error(f"Event {event_id} not found in database. Cannot process.")
            return

        # Simple state machine validation
        if event.status == "PROCESSED":
            logger.info(f"Event {event_id} is already processed. Ignoring.")
            return
        
        if event.status == "PROCESSING":
            # In a real distributed system, we'd check lock timeouts here.
            logger.info(f"Event {event_id} is already being processed by another worker. Ignoring.")
            return

        # Mark as processing
        event.status = "PROCESSING"
        await db.commit()
        await db.refresh(event)

        # -------------------------------------------------------------
        # INSERT DOMAIN LOGIC HERE (e.g., Financial State Transitions)
        # -------------------------------------------------------------
        logger.info(f"Processing webhook: type={event.event_type}, razorpay_event_id={event.razorpay_event_id}")
        
        # For Phase 0.2, we just log that we processed it.
        # In future phases, this will trigger the Recovery Firewall state machine.
        
        # Mark as processed
        event.status = "PROCESSED"
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Successfully processed event {event_id}")

    except Exception as e:
        logger.error(f"Error processing event {event_id}: {str(e)}", exc_info=True)
        
        # Try to mark the event as FAILED
        try:
            stmt = select(RazorpayEvent).where(RazorpayEvent.id == event_id)
            result = await db.execute(stmt)
            event = result.scalar_one_or_none()
            
            if event:
                event.status = "FAILED"
                event.error_msg = str(e)
                event.processed_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(f"Marked event {event_id} as FAILED in the database.")
        except Exception as inner_e:
            logger.error(f"Failed to update event {event_id} status to FAILED: {str(inner_e)}")
