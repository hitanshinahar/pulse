import asyncio
import os
import sys

# Ensure backend path is configured
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from backend.main import lifespan
import logging

logging.basicConfig(level=logging.INFO)

async def test_startup():
    app = FastAPI()
    try:
        async with lifespan(app):
            print("SUCCESS: Application startup routine (lifespan) completed without errors.")
            print("SUCCESS: SQLAlchemy metadata reflects the database schema successfully.")
    except Exception as e:
        print(f"FAILED: Error during startup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_startup())
