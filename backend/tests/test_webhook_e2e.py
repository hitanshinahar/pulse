import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
import uuid
import hmac
import hashlib
import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

from backend.models import (
    FinancialObligation, 
    RecoveryDecision, 
    RecoveryExecution, 
    RazorpayEvent, 
    RecoveryOutcome,
    RecoveryModelVersion,
    Base
)
from backend.config import settings

from sqlalchemy.pool import StaticPool

# Override database for this test to use a shared in-memory SQLite DB
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:", 
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

import backend.database
backend.database.engine = engine
backend.database.AsyncSessionLocal = TestingSessionLocal

from backend.main import app
# Also patch the imported AsyncSessionLocal in the razorpay webhook module
import backend.webhooks.razorpay
backend.webhooks.razorpay.AsyncSessionLocal = TestingSessionLocal

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[backend.database.get_db] = override_get_db

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
async def test_webhook_payment_link_paid_e2e():
    # 1. Setup Data
    async with TestingSessionLocal() as db_session:
        # Create obligation
        obligation = FinancialObligation(
            razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
            amount=Decimal('150.00'),
            currency='INR',
            satisfied_amount=Decimal('0.00'),
            outstanding_amount=Decimal('150.00'),
            status="RECOVERY_ELIGIBLE",
            state_version=1
        )
        db_session.add(obligation)
        await db_session.flush()
    
        # Ensure Model Version exists
        model_version = RecoveryModelVersion(
            version="recovery_v1_0",
            dataset_version=1,
            algorithm="random_forest",
            artifact_uri="s3://test/model",
            artifact_checksum="checksum_test",
            active=True,
            feature_schema_version=1,
            metrics={"test": True}
        )
        # We use merge so it doesn't fail if it already exists in the real DB
        db_session.add(await db_session.merge(model_version))
        await db_session.flush()
    
        # Create Decision
        decision = RecoveryDecision(
            obligation_id=obligation.id,
            state_version=obligation.state_version,
            action="PAYMENT_LINK",
            baseline_probability=Decimal('0.10'),
            action_probability=Decimal('0.80'),
            incremental_probability=Decimal('0.70'),
            expected_incremental_amount=Decimal('105.00'),
            model_version="recovery_v1_0",
            feature_schema_version=1,
            llm_diagnosis={"reason": "test"},
            evidence={"data": "test"},
            status="EXECUTED"
        )
        db_session.add(decision)
        await db_session.flush()
    
        # Create Execution
        ref_id = f"PULSE-REC-{str(decision.id)[:24]}"
        plink_id = f"plink_{uuid.uuid4().hex[:14]}"
        
        execution = RecoveryExecution(
            decision_id=decision.id,
            obligation_id=obligation.id,
            action="PAYMENT_LINK",
            execution_status="AUTHORIZED_PENDING_EXECUTION",
            idempotency_key=str(uuid.uuid4()),
            razorpay_reference_id=ref_id,
            razorpay_payment_link_id=plink_id,
            short_url="https://rzp.io/test",
            state_version_at_check=obligation.state_version
        )
        db_session.add(execution)
        await db_session.commit()

    # 2. Simulate Razorpay Webhook Payload
    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    
    payload = {
        "entity": "event",
        "account_id": "acc_test123",
        "event": "payment_link.paid",
        "contains": [
            "payment_link",
            "payment",
            "order"
        ],
        "payload": {
            "payment_link": {
                "entity": {
                    "id": plink_id,
                    "reference_id": ref_id,
                    "order_id": obligation.razorpay_order_id,
                    "status": "paid"
                }
            },
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": obligation.razorpay_order_id,
                    "amount": 15000,
                    "currency": "INR",
                    "status": "captured"
                }
            },
            "order": {
                "entity": {
                    "id": obligation.razorpay_order_id,
                    "amount": 15000,
                    "status": "paid"
                }
            }
        },
        "created_at": 1690000000
    }
    
    payload_str = json.dumps(payload)
    
    # 3. Sign the payload
    # Mocking webhook secret for the test
    settings.RAZORPAY_WEBHOOK_SECRET = "test_secret"
    signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    event_id = f"ev_{uuid.uuid4().hex[:14]}"

    # 4. Fire Webhook
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/razorpay",
            content=payload_str,
            headers={
                "x-razorpay-signature": signature,
                "x-razorpay-event-id": event_id
            }
        )
    
    assert response.status_code == 200
    
    # 5. Wait for Background Task to finish
    await asyncio.sleep(0.5)
    
    # 6. Verify Results using a fresh session to avoid cache
    async with TestingSessionLocal() as session:
        # Check Event
        stmt = select(RazorpayEvent).where(RazorpayEvent.razorpay_event_id == event_id)
        event = (await session.execute(stmt)).scalar_one_or_none()
        assert event is not None
        assert event.status == "PROCESSED"
        
        # Check Obligation
        stmt = select(FinancialObligation).where(FinancialObligation.id == obligation.id)
        obl = (await session.execute(stmt)).scalar_one_or_none()
        assert obl.satisfied_amount == Decimal('150.00')
        assert obl.outstanding_amount == Decimal('0.00')
        assert obl.status == "SATISFIED"
        
        # Check Outcome
        stmt = select(RecoveryOutcome).where(RecoveryOutcome.execution_id == execution.id)
        outcome = (await session.execute(stmt)).scalar_one_or_none()
        assert outcome is not None
        assert outcome.outcome == "RECOVERED"
        assert outcome.attribution_type == "RECOVERY_ATTRIBUTED"
        assert outcome.amount_recovered == Decimal('150.00')
        assert outcome.evidence_event_id == event.id
        
        # Check Execution
        stmt = select(RecoveryExecution).where(RecoveryExecution.id == execution.id)
        exec_updated = (await session.execute(stmt)).scalar_one_or_none()
        assert exec_updated.execution_status == "RECOVERED"
