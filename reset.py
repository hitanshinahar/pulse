import asyncio, os
from dotenv import load_dotenv
import asyncpg

async def main():
    load_dotenv()
    url = os.environ.get('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    await conn.execute("UPDATE razorpay_events SET status='RECEIVED'")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
