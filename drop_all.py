import asyncio, os
from dotenv import load_dotenv
import asyncpg

async def main():
    load_dotenv()
    url = os.environ.get('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    for table in tables:
        await conn.execute(f"DROP TABLE IF EXISTS {table['tablename']} CASCADE")
    print("All tables dropped.")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
