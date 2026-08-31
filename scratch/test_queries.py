import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from backend.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def test_queries():
    async with AsyncSessionLocal() as db:
        queries = [
            "SELECT count(*) FROM recovery_executions",
            "SELECT count(*) FROM recovery_outcomes",
            "SELECT count(*) FROM financial_obligations",
            "SELECT count(*) FROM razorpay_events"
        ]
        
        for q in queries:
            try:
                res = await db.execute(text(q))
                count = res.scalar()
                print(f"SUCCESS: {q} -> count: {count}")
            except Exception as e:
                print(f"ERROR: {q} -> {e}")

if __name__ == "__main__":
    asyncio.run(test_queries())
