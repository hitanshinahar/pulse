from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from backend.config import settings

engine = None
AsyncSessionLocal = None

if settings.DATABASE_URL:
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    engine = create_async_engine(
        db_url, 
        echo=False,
        connect_args={"statement_cache_size": 0}
    )
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    if not AsyncSessionLocal:
        raise Exception("Database is not configured. Missing DATABASE_URL in environment.")
    async with AsyncSessionLocal() as session:
        yield session
