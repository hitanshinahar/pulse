import os
import asyncio
import asyncpg
import httpx
import hmac
import hashlib
from dotenv import load_dotenv

async def main():
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET").encode('utf-8')
    
    conn = await asyncpg.connect(db_url)
    row = await conn.fetchrow("SELECT razorpay_event_id, raw_payload FROM razorpay_events ORDER BY created_at DESC LIMIT 1")
    await conn.close()
    
    if not row:
        print("No events found in DB.")
        return
        
    event_id = row['razorpay_event_id']
    raw_payload = row['raw_payload']
    
    signature = hmac.new(secret, raw_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    
    print(f'Sending duplicate event ID: {event_id}')
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://pulse-1j48.onrender.com/api/v1/webhooks/razorpay',
            headers={
                'x-razorpay-event-id': event_id,
                'x-razorpay-signature': signature,
                'Content-Type': 'application/json'
            },
            content=raw_payload
        )
        print(f'Status: {resp.status_code}')
        print(f'Response: {resp.text}')

if __name__ == '__main__':
    asyncio.run(main())
