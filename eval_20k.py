import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.database import Base
from backend.services.seed_actions import seed_action_registry
from backend.services.dataset_generator import generate_synthetic_dataset
from backend.services.ml_predictor import train_model

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db_session:
        await seed_action_registry(db_session)
        print("Generating dataset (20,000 contexts)...")
        count = await generate_synthetic_dataset(db_session, seed=42, num_contexts=20000)
        print(f"Generated {count} records.")
        
        print("\nTraining and Evaluating Model...")
        model = await train_model(db_session, dataset_version=1)

if __name__ == "__main__":
    asyncio.run(main())
