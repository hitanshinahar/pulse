import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os

from backend.integrations.razorpay.client import verify_connection, RazorpayIntegrationError, RazorpayUpstreamError
from backend.database import engine, Base, get_db
from backend.webhooks.razorpay import router as razorpay_webhook_router
from backend.api import financial, recovery
from backend.models import RazorpayEvent
from backend.config import settings

# Configure basic logging without exposing sensitive data
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup if it's set
    if engine is not None:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully.")
    else:
        logger.warning("No DATABASE_URL configured. Database tables were NOT initialized.")
    yield
    # Cleanup on shutdown
    if engine is not None:
        await engine.dispose()

app = FastAPI(title="Recovery Firewall API", lifespan=lifespan)

# Include webhook routers
app.include_router(razorpay_webhook_router, prefix="/api/v1/webhooks")
app.include_router(financial.router)
app.include_router(recovery.router)

@app.get("/api/v1/health/razorpay")
def health_razorpay():
    """
    Verifies connectivity to Razorpay Test Mode.
    Does not return credentials or sensitive data.
    """
    logger.info("Received request to verify Razorpay connectivity.")
    try:
        # The verify_connection method makes a real authenticated API request
        is_connected = verify_connection()
        if is_connected:
            logger.info("Razorpay connectivity verified successfully.")
            return {"status": "success", "message": "Successfully authenticated with Razorpay Test Mode."}
    except RazorpayIntegrationError as e:
        logger.warning(f"Razorpay integration error during health check: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except RazorpayUpstreamError as e:
        logger.error(f"Razorpay upstream error during health check: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during health check: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred verifying Razorpay connectivity.")

# Inspection endpoints (Dev Only)
def check_dev_mode():
    if not os.environ.get("DEV_MODE") == "true":
        logger.warning("Attempted to access dev-only inspection endpoint without DEV_MODE=true")
        raise HTTPException(status_code=403, detail="Forbidden. This endpoint is for development use only.")

@app.get("/api/v1/events/razorpay")
async def list_razorpay_events(db: AsyncSession = Depends(get_db)):
    check_dev_mode()
    try:
        stmt = select(RazorpayEvent).order_by(RazorpayEvent.created_at.desc()).limit(100)
        result = await db.execute(stmt)
        events = result.scalars().all()
        return {"events": [e.to_dict() for e in events]}
    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/events/razorpay/{event_id}")
async def get_razorpay_event(event_id: str, db: AsyncSession = Depends(get_db)):
    check_dev_mode()
    try:
        stmt = select(RazorpayEvent).where(RazorpayEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving event: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
