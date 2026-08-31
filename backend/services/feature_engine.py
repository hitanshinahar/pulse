from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from backend.models import (
    FinancialObligation, 
    PaymentAttempt, 
    RecoveryFeatureSnapshot
)

FEATURE_SCHEMA_VERSION = 1

async def extract_features(db: AsyncSession, obligation_id: str) -> RecoveryFeatureSnapshot:
    """Extracts deterministic features and returns a persisted snapshot."""
    
    # 1. Fetch Obligation
    stmt = select(FinancialObligation).where(FinancialObligation.id == obligation_id)
    result = await db.execute(stmt)
    obligation = result.scalar_one_or_none()
    
    if not obligation:
        raise ValueError(f"Obligation {obligation_id} not found")
        
    # 2. Fetch Payment Attempts
    stmt = select(PaymentAttempt).where(
        PaymentAttempt.obligation_id == obligation_id
    ).order_by(desc(PaymentAttempt.created_at))
    result = await db.execute(stmt)
    attempts = result.scalars().all()
    
    now = datetime.now(timezone.utc)
    
    # Calculate Obligation Features
    amount_due = float(obligation.amount)
    outstanding_amount = float(obligation.outstanding_amount)
    obl_created_at = obligation.created_at.replace(tzinfo=timezone.utc) if obligation.created_at.tzinfo is None else obligation.created_at
    obligation_age_seconds = (now - obl_created_at).total_seconds()
    obligation_state = obligation.status
    
    # Calculate Payment Trajectory Features
    attempt_count = len(attempts)
    failed_attempts = [a for a in attempts if a.razorpay_status == 'failed']
    captured_attempts = [a for a in attempts if a.razorpay_status == 'captured']
    
    failed_attempt_count = len(failed_attempts)
    captured_attempt_count = len(captured_attempts)
    
    if attempts:
        first_attempt_created = attempts[0].created_at.replace(tzinfo=timezone.utc) if attempts[0].created_at.tzinfo is None else attempts[0].created_at
        last_attempt_age_seconds = (now - first_attempt_created).total_seconds()
    else:
        last_attempt_age_seconds = None
    
    last_failure = failed_attempts[0] if failed_attempts else None
    if last_failure:
        last_failure_created = last_failure.created_at.replace(tzinfo=timezone.utc) if last_failure.created_at.tzinfo is None else last_failure.created_at
        time_since_last_failure_seconds = (now - last_failure_created).total_seconds()
    else:
        time_since_last_failure_seconds = None
    
    # Failure Metadata
    # In a real integration, we'd parse Razorpay failure codes from the latest failed attempt's raw event or metadata.
    # For now, we will use default fallbacks based on status.
    failure_category = "unknown" if last_failure else None
    failure_code = None
    failure_reason = None
    payment_method = last_failure.payment_method if last_failure else (attempts[0].payment_method if attempts else None)
    
    # We would fetch historical behavior here based on customer_id if we had one.
    # Since we don't store customer ID currently, historical behavior is explicitly None.
    previous_obligation_count = None
    previous_success_count = None
    previous_failure_count = None
    historical_success_rate = None
    historical_average_amount = None
    
    # Temporal Features
    hour_of_day = now.hour
    day_of_week = now.weekday()
    
    features_dict = {
        "amount_due": amount_due,
        "outstanding_amount": outstanding_amount,
        "obligation_age_seconds": obligation_age_seconds,
        "obligation_state": obligation_state,
        "attempt_count": attempt_count,
        "failed_attempt_count": failed_attempt_count,
        "captured_attempt_count": captured_attempt_count,
        "last_attempt_age_seconds": last_attempt_age_seconds,
        "time_since_last_failure_seconds": time_since_last_failure_seconds,
        "failure_category": failure_category,
        "failure_code": failure_code,
        "failure_reason": failure_reason,
        "payment_method": payment_method,
        "previous_obligation_count": previous_obligation_count,
        "previous_success_count": previous_success_count,
        "previous_failure_count": previous_failure_count,
        "historical_success_rate": historical_success_rate,
        "historical_average_amount": historical_average_amount,
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week
    }
    
    snapshot = RecoveryFeatureSnapshot(
        obligation_id=obligation.id,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        features=features_dict
    )
    
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    
    return snapshot
