import asyncio
import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.future import select

from backend.config import settings
from backend.models import (
    RazorpayEvent,
    RecoveryExecution,
    RecoveryOutcome,
    FinancialObligation
)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def check():
    async with AsyncSessionLocal() as db:
        obligation_id = 'b110983e-40e8-49e8-b740-26ebe1193b34'
        execution_id = '857eb707-1d36-485a-a96a-29052cdf3b5e'
        reference_id = 'PULSE-REC-857eb707-1d36-485a-a96a-29052c'
        plink_id = 'plink_TWIMNNkpGoSL5t'

        print("=== 1. RazorpayEvent ===")
        stmt = select(RazorpayEvent).where(
            RazorpayEvent.raw_payload.like(f"%{plink_id}%")
        )
        res = await db.execute(stmt)
        events = res.scalars().all()
        for e in events:
            payload = e.parsed_payload.get('payload', {})
            plink_entity = payload.get('payment_link', {}).get('entity', {})
            pay_entity = payload.get('payment', {}).get('entity', {})
            order_entity = payload.get('order', {}).get('entity', {})
            
            p_id = pay_entity.get('id')
            p_link = plink_entity.get('id')
            o_id = order_entity.get('id') or pay_entity.get('order_id')
            r_id = plink_entity.get('reference_id')
            
            print(f"Event ID: {e.id}")
            print(f"  Type: {e.event_type}")
            print(f"  Status: {e.status}")
            print(f"  Created At: {e.created_at}")
            print(f"  Payment ID: {p_id}")
            print(f"  Payment Link ID: {p_link}")
            print(f"  Order ID: {o_id}")
            print(f"  Reference ID: {r_id}")
            print("---")

        print("=== 2. RecoveryExecution ===")
        stmt = select(RecoveryExecution).where(RecoveryExecution.id == execution_id)
        res = await db.execute(stmt)
        exec_record = res.scalars().first()
        if exec_record:
            print(f"execution_id: {exec_record.id}")
            print(f"status: {exec_record.execution_status}")
            print(f"razorpay_reference_id: {exec_record.razorpay_reference_id}")
            print(f"razorpay_payment_link_id: {exec_record.razorpay_payment_link_id}")
            print(f"short_url: {exec_record.short_url}")
            print(f"payment_link_created_at: {exec_record.payment_link_created_at}")
        else:
            print("Not found")

        print("=== 3. RecoveryOutcome ===")
        stmt = select(RecoveryOutcome).where(RecoveryOutcome.execution_id == execution_id)
        res = await db.execute(stmt)
        outcomes = res.scalars().all()
        for o in outcomes:
            print(f"outcome: {o.outcome}")
            print(f"attribution_type: {o.attribution_type}")
            print(f"payment_id: {o.payment_id}")
            print(f"amount_recovered: {o.amount_recovered}")
            print(f"recovered_at: {o.recovered_at}")
            print(f"time_to_recovery_seconds: {o.time_to_recovery_seconds}")
            print(f"evidence_event_id: {o.evidence_event_id}")

        print("=== 4. FinancialObligation ===")
        stmt = select(FinancialObligation).where(FinancialObligation.id == obligation_id)
        res = await db.execute(stmt)
        ob = res.scalars().first()
        if ob:
            print(f"obligation_id: {ob.id}")
            print(f"amount: {ob.amount}")
            print(f"satisfied_amount: {ob.satisfied_amount}")
            print(f"outstanding_amount: {ob.outstanding_amount}")
            print(f"state: {ob.status}")
            print(f"version: {ob.state_version}")
        else:
            print("Not found")

if __name__ == "__main__":
    asyncio.run(check())
