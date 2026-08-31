import asyncio
import os
from dotenv import load_dotenv
import asyncpg

async def main():
    load_dotenv()
    url = os.environ.get('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    
    obs = await conn.fetch('SELECT * FROM financial_obligations')
    print(f"Obligations: {len(obs)}")
    for o in obs: print(dict(o))
        
    ats = await conn.fetch('SELECT * FROM payment_attempts')
    print(f"Attempts: {len(ats)}")
    for a in ats: print(dict(a))
    
    sts = await conn.fetch('SELECT * FROM obligation_state_transitions')
    print(f"Transitions: {len(sts)}")
    for s in sts: print(dict(s))
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
