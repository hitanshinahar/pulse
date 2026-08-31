from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import get_db
from backend.models import RecoveryFeatureSnapshot, RecoveryDecision, RecoveryModelVersion
from backend.services.feature_engine import extract_features
from backend.services.decision_engine import evaluate_recovery_actions
from backend.services.ml_predictor import predict

router = APIRouter(prefix="/api/v1/recovery", tags=["recovery"])

@router.get("/features/{obligation_id}")
async def get_features(obligation_id: str, db: AsyncSession = Depends(get_db)):
    # Look for existing snapshot or generate a fresh one
    snapshot = await extract_features(db, obligation_id)
    return {
        "id": str(snapshot.id),
        "obligation_id": str(snapshot.obligation_id),
        "feature_schema_version": snapshot.feature_schema_version,
        "features": snapshot.features,
        "created_at": snapshot.created_at
    }

@router.get("/prediction/{obligation_id}")
async def get_prediction(obligation_id: str, candidate_action: str = "PAYMENT_LINK", db: AsyncSession = Depends(get_db)):
    snapshot = await extract_features(db, obligation_id)
    
    stmt = select(RecoveryModelVersion).where(RecoveryModelVersion.active == True)
    result = await db.execute(stmt)
    model_record = result.scalar_one_or_none()
    
    if not model_record:
        raise HTTPException(status_code=500, detail="No active ML model found")
        
    prob = predict(model_record, snapshot.features, candidate_action)
    
    return {
        "obligation_id": obligation_id,
        "candidate_action": candidate_action,
        "probability": prob,
        "model_version": model_record.version,
        "feature_schema_version": snapshot.feature_schema_version
    }

@router.post("/decision/{obligation_id}")
async def create_decision(obligation_id: str, db: AsyncSession = Depends(get_db)):
    try:
        decision = await evaluate_recovery_actions(db, obligation_id)
        return {
            "id": str(decision.id),
            "obligation_id": str(decision.obligation_id),
            "action": decision.action,
            "baseline_probability": decision.baseline_probability,
            "action_probability": decision.action_probability,
            "incremental_probability": decision.incremental_probability,
            "expected_incremental_amount": decision.expected_incremental_amount,
            "state_version": decision.state_version,
            "model_version": decision.model_version,
            "status": decision.status,
            "llm_diagnosis": decision.llm_diagnosis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/decisions/{obligation_id}")
async def get_decisions(obligation_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(RecoveryDecision).where(RecoveryDecision.obligation_id == obligation_id)
    result = await db.execute(stmt)
    decisions = result.scalars().all()
    
    return [
        {
            "id": str(d.id),
            "action": d.action,
            "status": d.status,
            "incremental_probability": d.incremental_probability,
            "expected_incremental_amount": d.expected_incremental_amount,
            "created_at": d.created_at
        } for d in decisions
    ]
