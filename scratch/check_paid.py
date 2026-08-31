import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from backend.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def check():
    async with AsyncSessionLocal() as db:
        stmt = text("SELECT count(*) FROM razorpay_events WHERE event_type = 'payment_link.paid'")
        res = await db.execute(stmt)
        print("Count payment_link.paid:", res.scalar())

if __name__ == "__main__":
    asyncio.run(check())
