import logging
import json
from fastapi import APIRouter, Request, Header, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import razorpay

from backend.config import settings
from backend.database import get_db
from backend.models import RazorpayEvent
from backend.services.financial_state import process_razorpay_event
from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()

# The razorpay utility is not instantiated with keys, as verify_webhook_signature only needs the secret.
rzp_client = razorpay.Client(auth=("dummy", "dummy"))

@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str = Header(..., alias="x-razorpay-signature"),
    x_razorpay_event_id: str = Header(..., alias="x-razorpay-event-id"),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a real Razorpay webhook event securely.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured.")
        raise HTTPException(status_code=500, detail="Webhook configuration error")

    # 1. Read raw request body
    raw_body_bytes = await request.body()
    raw_body_str = raw_body_bytes.decode("utf-8")

    # 2. Verify signature
    try:
        rzp_client.utility.verify_webhook_signature(
            raw_body_str,
            x_razorpay_signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        logger.warning(f"Invalid webhook signature for event ID: {x_razorpay_event_id}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error during signature verification: {str(e)}")
        raise HTTPException(status_code=400, detail="Verification failed")

    # 3. Parse JSON payload securely
    try:
        parsed_payload = json.loads(raw_body_str)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON payload for event ID: {x_razorpay_event_id}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = parsed_payload.get("event")
    if not event_type:
        logger.warning(f"Webhook missing 'event' type field. Event ID: {x_razorpay_event_id}")
        raise HTTPException(status_code=400, detail="Missing event type")

    # 4. Persist event idempotently
    logger.info(f"Received verified webhook: event_type={event_type}, razorpay_event_id={x_razorpay_event_id}")
    
    new_event = RazorpayEvent(
        razorpay_event_id=x_razorpay_event_id,
        event_type=event_type,
        raw_payload=raw_body_str,
        parsed_payload=parsed_payload,
        status="RECEIVED"
    )

    try:
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
    except IntegrityError:
        # Idempotency constraint hit: event already exists
        await db.rollback()
        logger.info(f"Duplicate webhook delivery detected and ignored for event ID: {x_razorpay_event_id}")
        # Acknowledge immediately to prevent further retries
        return JSONResponse(status_code=200, content={"status": "already_processed"})
    except Exception as e:
        logger.error(f"Failed to persist event {x_razorpay_event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error during ingestion")

    # 5. Hand off processing to a background task with a fresh session
    async def run_webhook_processor(event_id: str):
        async with AsyncSessionLocal() as session:
            await process_razorpay_event(session, event_id)

    background_tasks.add_task(run_webhook_processor, str(new_event.id))

    # 6. Acknowledge receipt quickly
    return JSONResponse(status_code=200, content={"status": "ok"})
