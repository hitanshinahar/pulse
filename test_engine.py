import asyncio
import os
import logging
from dotenv import load_dotenv

from backend.database import AsyncSessionLocal
from backend.services.financial_state import run_processor

logging.basicConfig(level=logging.INFO)

async def main():
    load_dotenv()
    print("Running processor...")
    async with AsyncSessionLocal() as db:
        count = await run_processor(db, limit=10)
        print(f"Processed {count} events.")

if __name__ == '__main__':
    asyncio.run(main())
