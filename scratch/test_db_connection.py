import asyncio
from backend.database import engine
from sqlalchemy import text

async def main():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT pg_catalog.version()"))
            version = result.scalar()
            print(f"DATABASE_CONNECTION_OK: {version}")
    except Exception as e:
        print(f"DATABASE_CONNECTION_FAIL: {str(e)}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
