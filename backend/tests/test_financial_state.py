import pytest
from decimal import Decimal
import uuid
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from backend.models import RazorpayEvent, FinancialObligation, PaymentAttempt, ObligationStateTransition, Base
from backend.services.financial_state import _process_event_logic, parse_currency_amount

import pytest_asyncio

# In-memory SQLite for testing
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

# Mocks
async def mock_reconcile_order(order_id: str):
    return {
        "id": order_id,
        "amount": 5000,
        "currency": "INR",
        "receipt": "Rec_123",
        "status": "created",
        "attempts": 1
    }

@pytest.fixture(autouse=True)
def patch_reconcile(monkeypatch):
    monkeypatch.setattr("backend.services.financial_state.reconcile_order_with_razorpay", mock_reconcile_order)

def create_event(event_type: str, payment_status: str, payment_id: str, order_id: str, amount: int = 5000) -> RazorpayEvent:
    return RazorpayEvent(
        id=uuid.uuid4(),
        razorpay_event_id=f"evt_{uuid.uuid4()}",
        event_type=event_type,
        raw_payload="{}",
        parsed_payload={
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "status": payment_status,
                        "amount": amount,
                        "currency": "INR",
                        "method": "upi"
                    }
                }
            }
        },
        status="RECEIVED"
    )

@pytest.mark.asyncio
async def test_scenario_a_payment_captured():
    """Scenario A: Payment captured -> obligation satisfied"""
    async with AsyncSessionLocal() as db:
        event = create_event("payment.captured", "captured", "pay_1", "order_1")
        await _process_event_logic(db, event)
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        assert ob.status == "SATISFIED"
        assert ob.satisfied_amount == Decimal('50.00')
        assert ob.outstanding_amount == Decimal('0.00')

@pytest.mark.asyncio
async def test_scenario_b_payment_failed():
    """Scenario B: Payment failed -> obligation remains outstanding"""
    async with AsyncSessionLocal() as db:
        event = create_event("payment.failed", "failed", "pay_2", "order_2")
        await _process_event_logic(db, event)
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        assert ob.status == "RECOVERY_ELIGIBLE"
        assert ob.satisfied_amount == Decimal('0.00')
        assert ob.outstanding_amount == Decimal('50.00')

@pytest.mark.asyncio
async def test_scenario_c_failed_then_captured():
    """Scenario C: Failed payment followed by successful payment -> same obligation -> final state satisfied"""
    async with AsyncSessionLocal() as db:
        event1 = create_event("payment.failed", "failed", "pay_3", "order_3")
        await _process_event_logic(db, event1)
        
        event2 = create_event("payment.captured", "captured", "pay_4", "order_3")
        await _process_event_logic(db, event2)
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        assert ob.status == "SATISFIED"
        assert ob.satisfied_amount == Decimal('50.00')
        assert ob.outstanding_amount == Decimal('0.00')
        
        attempts = (await db.execute(select(PaymentAttempt))).scalars().all()
        assert len(attempts) == 2

@pytest.mark.asyncio
async def test_scenario_d_duplicate_webhook():
    """Scenario D & E: Duplicate webhook -> no duplicate payment -> no duplicate satisfied amount"""
    async with AsyncSessionLocal() as db:
        event1 = create_event("payment.captured", "captured", "pay_5", "order_5")
        await _process_event_logic(db, event1)
        # Process the EXACT SAME payload again
        event2 = create_event("payment.captured", "captured", "pay_5", "order_5")
        await _process_event_logic(db, event2)
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        assert ob.satisfied_amount == Decimal('50.00')
        
        attempts = (await db.execute(select(PaymentAttempt))).scalars().all()
        assert len(attempts) == 1

@pytest.mark.asyncio
async def test_scenario_f_out_of_order():
    """Scenario F: Out-of-order events -> state remains financially consistent"""
    async with AsyncSessionLocal() as db:
        # Received captured first
        event1 = create_event("payment.captured", "captured", "pay_6", "order_6")
        await _process_event_logic(db, event1)
        
        # Received an older failed attempt later
        event2 = create_event("payment.failed", "failed", "pay_6_old", "order_6")
        await _process_event_logic(db, event2)
        
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        # The failed attempt should NOT override the SATISFIED state
        assert ob.status == "SATISFIED"
        assert ob.satisfied_amount == Decimal('50.00')
        
@pytest.mark.asyncio
async def test_scenario_h_overpayment():
    """Scenario H: Overpayment explicitly represented"""
    async with AsyncSessionLocal() as db:
        # Payment 1
        event1 = create_event("payment.captured", "captured", "pay_7", "order_7")
        await _process_event_logic(db, event1)
        
        # Payment 2 (extra payment on same order)
        event2 = create_event("payment.captured", "captured", "pay_8", "order_7")
        await _process_event_logic(db, event2)
        
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        assert ob.status == "OVER_COLLECTED"
        assert ob.satisfied_amount == Decimal('100.00')
        assert ob.outstanding_amount == Decimal('-50.00')

@pytest.mark.asyncio
async def test_scenario_j_state_version():
    """Scenario J: Every legitimate state mutation increments exactly once."""
    async with AsyncSessionLocal() as db:
        # Step 1: Initial creation (v1), immediately becomes RECOVERY_ELIGIBLE (v2)
        event1 = create_event("payment.failed", "failed", "pay_9", "order_9")
        await _process_event_logic(db, event1)
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        # Created -> UNRESOLVED -> RECOVERY_ELIGIBLE is 1 state change + 1 creation = v2
        assert ob.state_version == 2
        
        # Step 2: Payment captured -> SATISFIED (v3)
        event2 = create_event("payment.captured", "captured", "pay_10", "order_9")
        await _process_event_logic(db, event2)
        await db.commit()
        
        await db.refresh(ob)
        assert ob.state_version == 3
        
        # Ensure transitions were recorded
        transitions = (await db.execute(select(ObligationStateTransition).order_by(ObligationStateTransition.created_at))).scalars().all()
        assert len(transitions) == 2
        assert transitions[0].new_state == "RECOVERY_ELIGIBLE"
        assert transitions[1].new_state == "SATISFIED"

@pytest.mark.asyncio
async def test_scenario_partial_payment():
    """Scenario K: Underpayment (Partial Payment)"""
    async with AsyncSessionLocal() as db:
        # Obligation is 50.00. Payment is 20.00.
        event1 = create_event("payment.captured", "captured", "pay_11", "order_11", amount=2000)
        await _process_event_logic(db, event1)
        await db.commit()
        
        from sqlalchemy.future import select
        ob = (await db.execute(select(FinancialObligation))).scalar_one()
        assert ob.status == "PARTIALLY_SATISFIED"
        assert ob.satisfied_amount == Decimal('20.00')
        assert ob.outstanding_amount == Decimal('30.00')
