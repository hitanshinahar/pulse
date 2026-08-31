import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from backend.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def check():
    async with AsyncSessionLocal() as db:
        stmt = text("SELECT id, event_type, status, created_at, raw_payload FROM razorpay_events ORDER BY created_at DESC LIMIT 5")
        res = await db.execute(stmt)
        for row in res.fetchall():
            print(row[0], row[1], row[2], row[3])

if __name__ == "__main__":
    asyncio.run(check())
