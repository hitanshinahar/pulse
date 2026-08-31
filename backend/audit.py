import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:studyingisimportantthanplaying@db.bwxwwyhrlxesfnwlobqk.supabase.co:5432/postgres"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def main():
    async with AsyncSessionLocal() as db:
        # Check recovery_executions
        print("--- recovery_executions columns ---")
        stmt = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'recovery_executions'")
        res = await db.execute(stmt)
        cols = res.all()
        if cols:
            for c in cols:
                print(f"{c[0]} ({c[1]})")
        else:
            print("TABLE DOES NOT EXIST")
            
        print("\n--- recovery_outcomes columns ---")
        stmt = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'recovery_outcomes'")
        res = await db.execute(stmt)
        cols = res.all()
        if cols:
            for c in cols:
                print(f"{c[0]} ({c[1]})")
        else:
            print("TABLE DOES NOT EXIST")

if __name__ == "__main__":
    asyncio.run(main())
