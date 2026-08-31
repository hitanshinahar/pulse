import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:studyingisimportantthanplaying@db.bwxwwyhrlxesfnwlobqk.supabase.co:5432/postgres"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def main():
    async with AsyncSessionLocal() as db:
        print("--- recovery_executions columns ---")
        stmt = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'recovery_executions'")
        res = await db.execute(stmt)
        for c in res.all(): print(f"{c[0]} ({c[1]})")

        print("\n--- recovery_executions unique constraints ---")
        stmt = text("""
            SELECT tc.constraint_name, kcu.column_name 
            FROM information_schema.table_constraints tc 
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name 
            WHERE tc.table_name = 'recovery_executions' AND tc.constraint_type = 'UNIQUE'
        """)
        res = await db.execute(stmt)
        for c in res.all(): print(f"{c[0]} -> {c[1]}")

        print("\n--- recovery_outcomes columns ---")
        stmt = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'recovery_outcomes'")
        res = await db.execute(stmt)
        for c in res.all(): print(f"{c[0]} ({c[1]})")

        print("\n--- recovery_outcomes foreign keys ---")
        stmt = text("""
            SELECT tc.constraint_name, kcu.column_name 
            FROM information_schema.table_constraints tc 
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name 
            WHERE tc.table_name = 'recovery_outcomes' AND tc.constraint_type = 'FOREIGN KEY'
        """)
        res = await db.execute(stmt)
        for c in res.all(): print(f"{c[0]} -> {c[1]}")
        
        print("\n--- Phase 1C existing rows count ---")
        stmt = text("SELECT count(*) FROM recovery_executions")
        res = await db.execute(stmt)
        print(f"recovery_executions count: {res.scalar()}")
        
if __name__ == "__main__":
    asyncio.run(main())
