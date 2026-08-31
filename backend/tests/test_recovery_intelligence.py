import pytest
import os
from unittest.mock import patch
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

from backend.database import Base
from backend.models import (
    FinancialObligation, 
    PaymentAttempt, 
    RecoveryActionDefinition,
    RecoveryModelVersion,
    RecoveryDecision
)
from backend.services.seed_actions import seed_action_registry
from backend.services.dataset_generator import generate_synthetic_dataset
from backend.services.ml_predictor import train_model
from backend.services.decision_engine import evaluate_recovery_actions
from backend.services.llm_investigator import LLMDiagnosis

import pytest_asyncio

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@pytest.fixture(autouse=True)
def setup_db():
    import asyncio
    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init())
    yield
    async def cleanup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(cleanup())

@pytest.mark.asyncio
async def test_recovery_pipeline():
    async with AsyncSessionLocal() as db_session:
        # 1. Seed Actions
        await seed_action_registry(db_session)
        stmt = select(RecoveryActionDefinition)
        res = await db_session.execute(stmt)
        assert len(res.scalars().all()) == 2
        
        # 2. Generate Dataset
        count = await generate_synthetic_dataset(db_session, seed=123, num_contexts=50)
        assert count == 100 # 50 WAIT, 50 PAYMENT_LINK
        
        # 3. Train ML Model
        model = await train_model(db_session, dataset_version=1)
        assert model.active == True
        assert "policy_learned" in model.metrics
        
        # 4. Create an Obligation
        obl = FinancialObligation(
            razorpay_order_id="order_test_recovery",
            amount=1000.0,
            currency="INR",
            satisfied_amount=0.0,
            outstanding_amount=1000.0,
            status="RECOVERY_ELIGIBLE",
            state_version=1
        )
        db_session.add(obl)
        
        attempt = PaymentAttempt(
            razorpay_payment_id="pay_test_recovery",
            razorpay_order_id="order_test_recovery",
            obligation=obl,
            amount=1000.0,
            currency="INR",
            razorpay_status="failed",
            payment_method="upi"
        )
        db_session.add(attempt)
        await db_session.commit()
        await db_session.refresh(obl)
        
        # 5. Evaluate Decision with Mocked LLM
        mock_diagnosis = LLMDiagnosis(
            failure_category="insufficient_funds",
            diagnostic_confidence=0.9,
            evidence=["mocked evidence"],
            uncertainty=False
        )
        
        with patch('backend.services.decision_engine.diagnose_failure') as mock_llm:
            mock_llm.return_value = mock_diagnosis
            decision = await evaluate_recovery_actions(db_session, str(obl.id))
            
        assert decision.action in ["WAIT", "PAYMENT_LINK"]
        assert decision.status == "PROPOSED"
        assert decision.llm_diagnosis["failure_category"] == "insufficient_funds"
        assert float(decision.baseline_probability) >= 0.0
