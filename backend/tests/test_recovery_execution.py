import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from razorpay.errors import BadRequestError, ServerError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    FinancialObligation,
    RecoveryDecision,
    RecoveryExecution,
    RecoveryPolicy,
    RazorpayEvent
)
from backend.services.recovery_executor import execute_recovery
from backend.services.recovery_outcome import attribute_payment_to_recovery

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.models import Base
import pytest_asyncio

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@pytest_asyncio.fixture(autouse=True)
async def db_setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def sample_db_data(db_session: AsyncSession):
    # Base policy
    policy = RecoveryPolicy(
        max_autonomous_amount=Decimal('10000.00'),
        max_actions_per_obligation=2,
        cooldown_seconds=0,
        allowed_actions=["PAYMENT_LINK"],
        require_human_above_amount=True,
        enabled=True
    )
    db_session.add(policy)

    # Base obligation
    obligation = FinancialObligation(
        id=uuid.uuid4(),
        razorpay_order_id="order_test_rec1",
        amount=Decimal('100.00'),
        currency="INR",
        satisfied_amount=Decimal('0.00'),
        outstanding_amount=Decimal('100.00'),
        status="RECOVERY_ELIGIBLE",
        state_version=2
    )
    db_session.add(obligation)

    # Base decision
    decision = RecoveryDecision(
        id=uuid.uuid4(),
        obligation_id=obligation.id,
        state_version=2,
        action="PAYMENT_LINK",
        baseline_probability=Decimal('0.1'),
        action_probability=Decimal('0.5'),
        incremental_probability=Decimal('0.4'),
        expected_incremental_amount=Decimal('40.00'),
        model_version="v1",
        feature_schema_version=1,
        llm_diagnosis={},
        evidence={},
        status="APPROVED"
    )
    db_session.add(decision)

    # Base execution
    execution = RecoveryExecution(
        id=uuid.uuid4(),
        decision_id=decision.id,
        obligation_id=obligation.id,
        action="PAYMENT_LINK",
        execution_status="AUTHORIZED_PENDING_EXECUTION",
        idempotency_key="ik_123",
        state_version_at_check=2
    )
    db_session.add(execution)
    
    await db_session.commit()
    return {
        "policy": policy,
        "obligation": obligation,
        "decision": decision,
        "execution": execution
    }

@pytest.mark.asyncio
async def test_execute_recovery_success(db_session, sample_db_data):
    execution = sample_db_data["execution"]
    
    mock_client = MagicMock()
    mock_client.payment_link.create.return_value = {
        "id": "plink_test_123",
        "short_url": "https://rzp.io/i/test",
        "status": "created"
    }

    with patch("backend.services.recovery_executor.get_razorpay_client", return_value=mock_client):
        result = await execute_recovery(db_session, str(execution.id))
        
    assert result.execution_status == "EXECUTED"
    assert result.razorpay_payment_link_id == "plink_test_123"
    assert result.short_url == "https://rzp.io/i/test"
    assert result.razorpay_reference_id.startswith("PULSE-REC-")
    
    # Assert correct payload structure sent
    create_args = mock_client.payment_link.create.call_args[0][0]
    assert create_args["amount"] == 10000 # 100.00 * 100
    assert create_args["currency"] == "INR"
    assert create_args["reference_id"] == result.razorpay_reference_id

@pytest.mark.asyncio
async def test_execute_recovery_stale_state(db_session, sample_db_data):
    obligation = sample_db_data["obligation"]
    execution = sample_db_data["execution"]
    
    # Simulate state change
    obligation.state_version = 3
    await db_session.commit()
    
    result = await execute_recovery(db_session, str(execution.id))
    
    assert result.execution_status == "EXECUTION_BLOCKED_STALE_STATE"
    assert result.razorpay_payment_link_id is None

@pytest.mark.asyncio
async def test_execute_recovery_4xx_failure(db_session, sample_db_data):
    execution = sample_db_data["execution"]
    
    mock_client = MagicMock()
    mock_client.payment_link.create.side_effect = BadRequestError("Invalid currency")

    with patch("backend.services.recovery_executor.get_razorpay_client", return_value=mock_client):
        result = await execute_recovery(db_session, str(execution.id))
        
    assert result.execution_status == "EXECUTION_FAILED"

@pytest.mark.asyncio
async def test_execute_recovery_ambiguous_failure(db_session, sample_db_data):
    execution = sample_db_data["execution"]
    
    mock_client = MagicMock()
    mock_client.payment_link.create.side_effect = ServerError("Timeout")

    with patch("backend.services.recovery_executor.get_razorpay_client", return_value=mock_client):
        result = await execute_recovery(db_session, str(execution.id))
        
    assert result.execution_status == "EXECUTION_UNKNOWN"

@pytest.mark.asyncio
async def test_attribute_payment_to_recovery(db_session, sample_db_data):
    obligation = sample_db_data["obligation"]
    execution = sample_db_data["execution"]
    
    # Simulate executed state
    execution.execution_status = "EXECUTED"
    execution.razorpay_reference_id = f"REC-{execution.id.hex}"
    await db_session.commit()
    
    # Mock event
    event = RazorpayEvent(
        razorpay_event_id="ev_test_123",
        event_type="payment_link.paid",
        raw_payload="{}",
        parsed_payload={
            "payload": {
                "payment_link": {
                    "entity": {
                        "reference_id": execution.razorpay_reference_id
                    }
                },
                "payment": {
                    "entity": {
                        "id": "pay_test_456",
                        "amount": 10000
                    }
                }
            }
        },
        status="PROCESSED"
    )
    db_session.add(event)
    await db_session.commit()
    
    # We pretend financial state made outstanding 0
    obligation.outstanding_amount = Decimal('0.00')
    
    outcome = await attribute_payment_to_recovery(db_session, event, obligation)
    
    assert outcome is not None
    assert outcome.execution_id == execution.id
    assert outcome.attribution_type == "RECOVERY_ATTRIBUTED"
    assert outcome.outcome == "RECOVERED"
    assert outcome.amount_recovered == Decimal('100.00')
    
    # Execution status updated to RECOVERED
    assert execution.execution_status == "RECOVERED"
