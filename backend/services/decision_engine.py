import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models import (
    FinancialObligation,
    RecoveryActionDefinition,
    RecoveryModelVersion,
    RecoveryDecision
)
from backend.services.feature_engine import extract_features
from backend.services.ml_predictor import predict
from backend.services.llm_investigator import diagnose_failure, LLMDiagnosis

async def get_eligible_actions(db: AsyncSession, obligation: FinancialObligation):
    stmt = select(RecoveryActionDefinition).where(RecoveryActionDefinition.enabled == True)
    result = await db.execute(stmt)
    all_actions = result.scalars().all()
    
    eligible = []
    for action in all_actions:
        # Check eligibility
        if action.requires_outstanding_balance and obligation.outstanding_amount <= 0:
            continue
        if obligation.status in ["SATISFIED", "OVER_COLLECTED", "CLOSED"]:
            continue
            
        eligible.append(action)
        
    return eligible

async def evaluate_recovery_actions(db: AsyncSession, obligation_id: str) -> RecoveryDecision:
    # 1. Fetch obligation
    stmt = select(FinancialObligation).where(FinancialObligation.id == obligation_id)
    result = await db.execute(stmt)
    obligation = result.scalar_one_or_none()
    
    if not obligation:
        raise ValueError(f"Obligation {obligation_id} not found")

    # 2. Extract deterministic features
    feature_snapshot = await extract_features(db, obligation_id)
    features_dict = feature_snapshot.features
    
    # 3. Get LLM diagnosis
    try:
        diagnosis = await diagnose_failure(features_dict)
    except Exception:
        diagnosis = LLMDiagnosis(
            failure_category="unknown",
            diagnostic_confidence=0.0,
            evidence=[
                "LLM diagnosis unavailable; decision generated from deterministic "
                "recovery policy and prediction model."
            ],
            uncertainty=True,
        )
    
    # 4. Get active ML model
    stmt = select(RecoveryModelVersion).where(RecoveryModelVersion.active == True)
    result = await db.execute(stmt)
    model_record = result.scalar_one_or_none()
    
    if not model_record:
        raise ValueError("No active ML model found for recovery prediction.")
        
    # 5. Evaluate Actions
    eligible_actions = await get_eligible_actions(db, obligation)
    action_ids = [a.action_id for a in eligible_actions]
    
    # WAIT must always exist as the baseline
    if "WAIT" not in action_ids:
        # Fallback in case WAIT isn't seeded correctly, but it should be.
        baseline_prob = 0.0
    else:
        baseline_prob = predict(model_record, features_dict, "WAIT")
        
    best_action = "WAIT"
    best_incremental = 0.0
    action_prob = baseline_prob
    
    for action in eligible_actions:
        if action.action_id == "WAIT":
            continue
            
        prob = predict(model_record, features_dict, action.action_id)
        incremental = prob - baseline_prob
        
        if incremental > best_incremental:
            best_incremental = incremental
            best_action = action.action_id
            action_prob = prob
            
    expected_amount = Decimal(str(best_incremental)) * obligation.outstanding_amount
    
    # 6. Record Decision (PROPOSED)
    decision = RecoveryDecision(
        obligation_id=obligation.id,
        state_version=obligation.state_version,
        action=best_action,
        baseline_probability=Decimal(str(baseline_prob)),
        action_probability=Decimal(str(action_prob)),
        incremental_probability=Decimal(str(best_incremental)),
        expected_incremental_amount=expected_amount,
        model_version=model_record.version,
        feature_schema_version=feature_snapshot.feature_schema_version,
        llm_diagnosis=diagnosis.model_dump(),
        evidence=[], # Derived from LLM or rule engine if needed
        status="PROPOSED"
    )
    
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    
    return decision
