from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid

from backend.database import get_db
from backend.models import FinancialObligation, PaymentAttempt, ObligationStateTransition
from backend.services.revenue_at_risk import get_revenue_at_risk
from backend.services.financial_state import run_processor

router = APIRouter()

@router.get("/obligations")
async def list_obligations(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    stmt = select(FinancialObligation).order_by(FinancialObligation.created_at.desc())
    if status:
        stmt = stmt.where(FinancialObligation.status == status)
    
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    obligations = result.scalars().all()
    
    return {
        "data": [
            {
                "id": str(o.id),
                "merchant_reference": o.merchant_reference,
                "razorpay_order_id": o.razorpay_order_id,
                "amount": float(o.amount),
                "currency": o.currency,
                "satisfied_amount": float(o.satisfied_amount),
                "outstanding_amount": float(o.outstanding_amount),
                "status": o.status,
                "state_version": o.state_version,
                "created_at": o.created_at.isoformat(),
                "updated_at": o.updated_at.isoformat(),
            }
            for o in obligations
        ]
    }

@router.get("/obligations/{obligation_id}")
async def get_obligation(
    obligation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FinancialObligation).where(FinancialObligation.id == obligation_id)
    result = await db.execute(stmt)
    obligation = result.scalar_one_or_none()
    
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
        
    return {
        "id": str(obligation.id),
        "merchant_reference": obligation.merchant_reference,
        "razorpay_order_id": obligation.razorpay_order_id,
        "amount": float(obligation.amount),
        "currency": obligation.currency,
        "satisfied_amount": float(obligation.satisfied_amount),
        "outstanding_amount": float(obligation.outstanding_amount),
        "status": obligation.status,
        "state_version": obligation.state_version,
        "created_at": obligation.created_at.isoformat(),
        "updated_at": obligation.updated_at.isoformat(),
    }

@router.get("/obligations/{obligation_id}/timeline")
async def get_obligation_timeline(
    obligation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    # Get payment attempts
    stmt_attempts = select(PaymentAttempt).where(PaymentAttempt.obligation_id == obligation_id).order_by(PaymentAttempt.created_at.desc())
    res_attempts = await db.execute(stmt_attempts)
    attempts = res_attempts.scalars().all()
    
    # Get state transitions
    stmt_transitions = select(ObligationStateTransition).where(ObligationStateTransition.obligation_id == obligation_id).order_by(ObligationStateTransition.created_at.desc())
    res_transitions = await db.execute(stmt_transitions)
    transitions = res_transitions.scalars().all()
    
    return {
        "payment_attempts": [
            {
                "id": str(p.id),
                "razorpay_payment_id": p.razorpay_payment_id,
                "amount": float(p.amount),
                "currency": p.currency,
                "payment_method": p.payment_method,
                "razorpay_status": p.razorpay_status,
                "created_at": p.created_at.isoformat()
            } for p in attempts
        ],
        "state_transitions": [
            {
                "id": str(t.id),
                "previous_state": t.previous_state,
                "new_state": t.new_state,
                "previous_version": t.previous_version,
                "new_version": t.new_version,
                "reason": t.reason,
                "source": t.source,
                "triggering_event_id": str(t.triggering_event_id) if t.triggering_event_id else None,
                "created_at": t.created_at.isoformat()
            } for t in transitions
        ]
    }

@router.get("/revenue-at-risk")
async def get_revenue_at_risk_api(db: AsyncSession = Depends(get_db)):
    obligations = await get_revenue_at_risk(db)
    return {
        "data": [
            {
                "id": str(o.id),
                "razorpay_order_id": o.razorpay_order_id,
                "outstanding_amount": float(o.outstanding_amount),
                "currency": o.currency,
                "status": o.status
            }
            for o in obligations
        ],
        "total_outstanding_inr": sum(float(o.outstanding_amount) for o in obligations if o.currency == 'INR')
    }

@router.post("/process-events")
async def process_pending_events(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger the event processor. 
    Useful for testing or if the poller is disabled.
    """
    processed_count = await run_processor(db, limit=100)
    return {"status": "success", "processed_count": processed_count}
