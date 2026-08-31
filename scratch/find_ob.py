import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from backend.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def check():
    async with AsyncSessionLocal() as db:
        stmt = text("SELECT id, razorpay_order_id, amount, status FROM financial_obligations WHERE status = 'RECOVERY_ELIGIBLE' LIMIT 1")
        res = await db.execute(stmt)
        row = res.first()
        if row:
            print(f"FOUND: id={row[0]}, order_id={row[1]}, amount={row[2]}, status={row[3]}")
        else:
            print("NOT FOUND")

if __name__ == "__main__":
    asyncio.run(check())
