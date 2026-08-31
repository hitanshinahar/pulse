import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:studyingisimportantthanplaying@db.bwxwwyhrlxesfnwlobqk.supabase.co:5432/postgres"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def main():
    async with AsyncSessionLocal() as db:
        stmt = text("SELECT COUNT(*) as count FROM recovery_executions WHERE external_reference IS NOT NULL")
        res = await db.execute(stmt)
        count = res.scalar()
        
        if count > 0:
            print(f"FOUND {count} rows with external_reference IS NOT NULL")
            stmt = text("SELECT id, external_reference FROM recovery_executions WHERE external_reference IS NOT NULL LIMIT 10")
            res = await db.execute(stmt)
            for row in res.mappings():
                print(row)
        else:
            print("NO existing external_reference values found in production.")

if __name__ == "__main__":
    asyncio.run(main())
