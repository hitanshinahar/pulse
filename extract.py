import os
import asyncio
import asyncpg
import json
from dotenv import load_dotenv

async def main():
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    rows = await conn.fetch("SELECT razorpay_event_id, event_type, parsed_payload FROM razorpay_events ORDER BY created_at DESC LIMIT 5")
    await conn.close()
    
    for row in rows:
        print(f"--- Event: {row['event_type']} (ID: {row['razorpay_event_id']}) ---")
        try:
            payload = json.loads(row['parsed_payload']) if isinstance(row['parsed_payload'], str) else row['parsed_payload']
            entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            print(f"Payment ID: {entity.get('id')}")
            print(f"Order ID: {entity.get('order_id')}")
            print(f"Status: {entity.get('status')}")
        except Exception as e:
            print("Error parsing", e)
if __name__ == '__main__':
    asyncio.run(main())
