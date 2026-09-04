from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import get_db
from backend.models import (
    RecoveryFeatureSnapshot,
    RecoveryDecision,
    RecoveryModelVersion,
    RecoveryPolicy,
    FirewallEvaluation,
    RecoveryExecution,
)
from backend.services.feature_engine import extract_features
from backend.services.decision_engine import evaluate_recovery_actions
from backend.services.ml_predictor import predict
from backend.services.recovery_firewall import evaluate_decision
from backend.services.recovery_executor import execute_recovery
from backend.services.recovery_reconciler import reconcile_unknown_execution

from typing import Dict, Any


router = APIRouter(prefix="/api/v1/recovery", tags=["recovery"])


@router.get("/features/{obligation_id}")
async def get_features(
    obligation_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Look for existing snapshot or generate a fresh one
    snapshot = await extract_features(db, obligation_id)

    return {
        "id": str(snapshot.id),
        "obligation_id": str(snapshot.obligation_id),
        "feature_schema_version": snapshot.feature_schema_version,
        "features": snapshot.features,
        "created_at": snapshot.created_at,
    }


@router.get("/prediction/{obligation_id}")
async def get_prediction(
    obligation_id: str,
    candidate_action: str = "PAYMENT_LINK",
    db: AsyncSession = Depends(get_db),
):
    snapshot = await extract_features(db, obligation_id)

    stmt = select(RecoveryModelVersion).where(
        RecoveryModelVersion.active == True
    )
    result = await db.execute(stmt)
    model_record = result.scalar_one_or_none()

    if not model_record:
        raise HTTPException(
            status_code=500,
            detail="No active ML model found",
        )

    prob = predict(
        model_record,
        snapshot.features,
        candidate_action,
    )

    return {
        "obligation_id": obligation_id,
        "candidate_action": candidate_action,
        "probability": prob,
        "model_version": model_record.version,
        "feature_schema_version": snapshot.feature_schema_version,
    }


@router.post("/decision/{obligation_id}")
async def create_decision(
    obligation_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        decision = await evaluate_recovery_actions(
            db,
            obligation_id,
        )

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
            "llm_diagnosis": decision.llm_diagnosis,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/decisions/{obligation_id}")
async def get_decisions(
    obligation_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RecoveryDecision).where(
        RecoveryDecision.obligation_id == obligation_id
    )

    result = await db.execute(stmt)
    decisions = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "action": d.action,
            "status": d.status,
            "incremental_probability": d.incremental_probability,
            "expected_incremental_amount": d.expected_incremental_amount,
            "created_at": d.created_at,
        }
        for d in decisions
    ]


@router.post("/decisions/{decision_id}/evaluate")
async def evaluate_recovery_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates a PROPOSED decision through the Recovery Firewall.
    Does NOT execute external actions.
    """
    result = await evaluate_decision(
        db,
        decision_id,
    )

    return result


@router.get("/decisions/{decision_id}/audit")
async def get_decision_audit(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RecoveryDecision).where(
        RecoveryDecision.id == decision_id
    )

    decision = (
        await db.execute(stmt)
    ).scalar_one_or_none()

    if not decision:
        raise HTTPException(
            status_code=404,
            detail="Decision not found",
        )

    stmt_evals = (
        select(FirewallEvaluation)
        .where(
            FirewallEvaluation.decision_id == decision.id
        )
        .order_by(FirewallEvaluation.created_at)
    )

    evals = (
        await db.execute(stmt_evals)
    ).scalars().all()

    stmt_execs = select(RecoveryExecution).where(
        RecoveryExecution.decision_id == decision.id
    )

    execs = (
        await db.execute(stmt_execs)
    ).scalars().all()

    return {
        "decision": {
            "id": str(decision.id),
            "obligation_id": str(decision.obligation_id),
            "state_version": decision.state_version,
            "action": decision.action,
            "status": decision.status,
            "created_at": decision.created_at.isoformat(),
        },

        "evaluations": [
            {
                "result": e.result,
                "reason_code": e.reason_code,
                "checks": e.checks,
                "created_at": e.created_at.isoformat(),
            }
            for e in evals
        ],

        "executions": [
            {
                "id": str(ex.id),
                "status": ex.execution_status,
                "idempotency_key": ex.idempotency_key,
                "executed_at": (
                    ex.executed_at.isoformat()
                    if ex.executed_at
                    else None
                ),
            }
            for ex in execs
        ],
    }


@router.get("/policy")
async def get_active_policy(
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import desc

    stmt = (
        select(RecoveryPolicy)
        .order_by(desc(RecoveryPolicy.created_at))
        .limit(1)
    )

    policy = (
        await db.execute(stmt)
    ).scalar_one_or_none()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="No policy found",
        )

    return {
        "id": str(policy.id),
        "max_autonomous_amount": float(
            policy.max_autonomous_amount
        ),
        "max_actions_per_obligation":
            policy.max_actions_per_obligation,
        "cooldown_seconds":
            policy.cooldown_seconds,
        "allowed_actions":
            policy.allowed_actions,
        "require_human_above_amount":
            policy.require_human_above_amount,
        "enabled":
            policy.enabled,
    }


@router.post("/policy")
async def create_policy(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    if payload.get("max_autonomous_amount", -1) < 0:
        raise HTTPException(
            status_code=400,
            detail="Amount cannot be negative",
        )

    if payload.get("cooldown_seconds", -1) < 0:
        raise HTTPException(
            status_code=400,
            detail="Cooldown cannot be negative",
        )

    policy = RecoveryPolicy(
        max_autonomous_amount=payload.get(
            "max_autonomous_amount",
            10000,
        ),
        max_actions_per_obligation=payload.get(
            "max_actions_per_obligation",
            2,
        ),
        cooldown_seconds=payload.get(
            "cooldown_seconds",
            21600,
        ),
        allowed_actions=payload.get(
            "allowed_actions",
            ["PAYMENT_LINK"],
        ),
        require_human_above_amount=payload.get(
            "require_human_above_amount",
            True,
        ),
        enabled=payload.get(
            "enabled",
            True,
        ),
    )

    db.add(policy)
    await db.commit()

    return {
        "status": "success",
        "policy_id": str(policy.id),
    }


@router.post("/executions/{execution_id}/execute")
async def explicit_execute_recovery(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Explicitly execute an authorized recovery action.
    """
    execution = await execute_recovery(
        db,
        execution_id,
    )

    return {
        "id": str(execution.id),
        "status": execution.execution_status,
        "razorpay_reference_id":
            execution.razorpay_reference_id,
        "razorpay_payment_link_id":
            execution.razorpay_payment_link_id,
        "short_url":
            execution.short_url,
    }


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return execution state and outcome details.
    """
    stmt = select(RecoveryExecution).where(
        RecoveryExecution.id == execution_id
    )

    execution = (
        await db.execute(stmt)
    ).scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=404,
            detail="Execution not found",
        )

    return {
        "id": str(execution.id),
        "decision_id": str(execution.decision_id),
        "status": execution.execution_status,
        "razorpay_reference_id":
            execution.razorpay_reference_id,
        "razorpay_payment_link_id":
            execution.razorpay_payment_link_id,
        "short_url":
            execution.short_url,
        "executed_at": (
            execution.executed_at.isoformat()
            if execution.executed_at
            else None
        ),
    }


@router.post("/executions/{execution_id}/reconcile")
async def explicit_reconcile_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Explicitly reconcile an EXECUTION_UNKNOWN execution.
    """
    execution = await reconcile_unknown_execution(
        db,
        execution_id,
    )

    if not execution:
        raise HTTPException(
            status_code=404,
            detail="Execution not found",
        )

    return {
        "id": str(execution.id),
        "status": execution.execution_status,
    }