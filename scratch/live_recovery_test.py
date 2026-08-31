import asyncio
import uuid
import json
from unittest.mock import patch
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.future import select

from backend.config import settings
from backend.models import (
    FinancialObligation, RazorpayEvent, RecoveryDecision, RecoveryExecution, RecoveryPolicy, RecoveryModelVersion
)
from backend.services.financial_state import _process_event_logic
from backend.services.decision_engine import evaluate_recovery_actions
from backend.services.recovery_firewall import evaluate_decision
from backend.services.recovery_executor import execute_recovery
from backend.services.seed_actions import seed_action_registry

from backend.integrations.razorpay.client import get_razorpay_client

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def setup_policy(db):
    stmt = select(RecoveryPolicy).where(RecoveryPolicy.enabled == True)
    res = await db.execute(stmt)
    if not res.first():
        policy = RecoveryPolicy(
            max_autonomous_amount=Decimal('10000.00'),
            max_actions_per_obligation=5,
            cooldown_seconds=0,
            allowed_actions=["PAYMENT_LINK"],
            require_human_above_amount=True,
            enabled=True
        )
        db.add(policy)
        await db.commit()
        
    # Seed Actions
    await seed_action_registry(db)
    
    # Seed Model
    stmt = select(RecoveryModelVersion).where(RecoveryModelVersion.active == True)
    res = await db.execute(stmt)
    if not res.first():
        model = RecoveryModelVersion(
            version="v1.0.test",
            dataset_version=1,
            feature_schema_version=1,
            algorithm="xgboost",
            metrics={"auc": 0.9},
            artifact_uri="s3://dummy/model",
            artifact_checksum="checksum123",
            active=True
        )
        db.add(model)
        await db.commit()

async def create_eligible_obligation(db):
    client = get_razorpay_client()
    order_amount = 15000 # 150 INR
    receipt_id = f"rcpt_prod_{uuid.uuid4().hex[:8]}"
    
    # Create real order in Razorpay
    order_data = {
        "amount": order_amount,
        "currency": "INR",
        "receipt": receipt_id
    }
    rzp_order = await asyncio.to_thread(client.order.create, order_data)
    order_id = rzp_order['id']
    print(f"Created real Razorpay order: {order_id}")
    
    payment_id = f"pay_prod_test_{uuid.uuid4().hex[:8]}"
    
    event_payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": 15000,
                    "currency": "INR",
                    "status": "failed",
                    "method": "upi"
                }
            },
            "order": {
                "entity": {
                    "id": order_id,
                    "amount": 15000,
                    "currency": "INR",
                    "receipt": "rcpt_1"
                }
            }
        }
    }
    
    event = RazorpayEvent(
        razorpay_event_id=f"ev_{uuid.uuid4().hex[:10]}",
        event_type="payment.failed",
        raw_payload=json.dumps(event_payload),
        parsed_payload=event_payload,
        status="RECEIVED"
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    await _process_event_logic(db, event)
    event.status = "PROCESSED"
    await db.commit()
    
    stmt = select(FinancialObligation).where(FinancialObligation.razorpay_order_id == order_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def main():
    async with AsyncSessionLocal() as db:
        await setup_policy(db)
        
        # 1. Always create a new eligible obligation for a clean test
        print("Creating a new eligible obligation via event workflow...")
        obligation = await create_eligible_obligation(db)
        
        if not obligation or obligation.status != 'RECOVERY_ELIGIBLE':
            print("Failed to secure an eligible obligation.")
            return
            
        print(f"Obligation ID: {obligation.id}")
        
        # Check if an active execution already exists
        stmt = select(RecoveryExecution).where(
            RecoveryExecution.obligation_id == obligation.id,
            RecoveryExecution.execution_status == 'AUTHORIZED_PENDING_EXECUTION'
        )
        res = await db.execute(stmt)
        execution = res.scalars().first()
        
        if not execution:
            # 2. Intelligence Pipeline
            with patch('backend.services.decision_engine.predict') as mock_predict:
                def side_effect(model, features, action):
                    return 0.5 if action == "PAYMENT_LINK" else 0.1
                mock_predict.side_effect = side_effect
                decision = await evaluate_recovery_actions(db, str(obligation.id))
                
            print(f"Decision ID: {decision.id} | Action: {decision.action}")
            
            # 3. Firewall Evaluation
            firewall_eval = await evaluate_decision(db, decision.id)
            print(f"Firewall Result: {firewall_eval['result']}")
            
            if firewall_eval['result'] != "ALLOW":
                print(f"Firewall blocked! Reason: {firewall_eval['reason']}")
                return
                
            stmt = select(RecoveryExecution).where(RecoveryExecution.decision_id == decision.id)
            res = await db.execute(stmt)
            execution = res.scalars().first()
        else:
            print(f"Found existing authorized execution: {execution.id}")
            
        print(f"Execution ID: {execution.id} | Initial Status: {execution.execution_status}")
        
        # 4. Phase 1D Execution
        execution_result = await execute_recovery(db, str(execution.id))
        
        print(f"Final Execution Status: {execution_result.execution_status}")
        print(f"Razorpay Reference ID: {execution_result.razorpay_reference_id}")
        print(f"Razorpay Payment Link ID: {execution_result.razorpay_payment_link_id}")
        print(f"Short URL: {execution_result.short_url}")
        print(f"Amount: {obligation.amount}")
        print(f"Currency: {obligation.currency}")

if __name__ == "__main__":
    asyncio.run(main())
