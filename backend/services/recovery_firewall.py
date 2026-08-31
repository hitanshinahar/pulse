import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, desc
import sqlalchemy as sa

from backend.models import (
    RecoveryDecision,
    FinancialObligation,
    RecoveryPolicy,
    RecoveryActionDefinition,
    RecoveryExecution,
    FirewallEvaluation
)

DECISION_TTL_MINUTES = 60

async def _get_active_policy(db: AsyncSession) -> RecoveryPolicy:
    stmt = select(RecoveryPolicy).where(RecoveryPolicy.enabled == True).order_by(desc(RecoveryPolicy.created_at)).limit(1)
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    return policy

async def evaluate_decision(db: AsyncSession, decision_id: str) -> Dict[str, Any]:
    """
    Evaluates a RecoveryDecision through the deterministic firewall.
    Uses strict SELECT FOR UPDATE row-level locking to prevent race conditions.
    """
    
    # Check 1: Decision exists & Concurrency lock
    # Use normal blocking FOR UPDATE to serialize concurrent requests.
    stmt = select(RecoveryDecision).where(RecoveryDecision.id == decision_id).with_for_update()
    result = await db.execute(stmt)
    decision = result.scalar_one_or_none()
    
    if not decision:
        return _fail_closed(db, decision_id, "DECISION_NOT_FOUND", "Decision does not exist.")
        
    # Check 2: Decision status & Idempotency
    # If the decision is already evaluated, return the idempotent result.
    if decision.status != "PROPOSED":
        # It was already evaluated. Return the existing evaluation.
        stmt = select(FirewallEvaluation).where(FirewallEvaluation.decision_id == decision.id).order_by(desc(FirewallEvaluation.created_at)).limit(1)
        eval_res = (await db.execute(stmt)).scalar_one_or_none()
        if eval_res:
            return {
                "decision_id": str(decision_id),
                "result": eval_res.result,
                "reason_code": eval_res.reason_code,
                "reason": eval_res.reason,
                "checks": eval_res.checks,
                "state_version_expected": eval_res.state_version_expected,
                "state_version_actual": eval_res.state_version_actual
            }
        return _fail_closed(db, decision.id, "INVALID_STATUS", f"Decision status is {decision.status} but no evaluation found.")

    checks = {}
    
    try:
        # Load the latest financial obligation
        stmt = select(FinancialObligation).where(FinancialObligation.id == decision.obligation_id)
        result = await db.execute(stmt)
        obligation = result.scalar_one_or_none()
        
        if not obligation:
            return await _record_evaluation(db, decision, None, checks, "BLOCK", "SYSTEM_VALIDATION_FAILED", "Obligation not found")
            
        expected_version = decision.state_version
        actual_version = obligation.state_version
        
        # Check 11: Decision expiry
        now_utc = datetime.now(timezone.utc)
        # Ensure decision.created_at is aware
        created_at = decision.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
            
        decision_age = now_utc - created_at
        if decision_age > timedelta(minutes=DECISION_TTL_MINUTES):
            checks["decision_not_expired"] = False
            return await _record_evaluation(db, decision, obligation, checks, "EXPIRE", "DECISION_EXPIRED", f"Decision is older than TTL of {DECISION_TTL_MINUTES}m")
        checks["decision_not_expired"] = True

        # Check 3: State freshness (TOCTOU protection)
        if expected_version != actual_version:
            checks["state_fresh"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "STALE_FINANCIAL_STATE", f"Expected version {expected_version}, got {actual_version}")
        checks["state_fresh"] = True
        
        # Check 4: Outstanding amount
        if obligation.outstanding_amount <= 0:
            checks["outstanding_positive"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "NO_OUTSTANDING_BALANCE", "Obligation has no outstanding balance")
        checks["outstanding_positive"] = True
        
        # Check 5: Obligation state
        eligible_states = ["UNRESOLVED", "RECOVERY_ELIGIBLE", "PARTIALLY_SATISFIED"]
        if obligation.status not in eligible_states:
            checks["obligation_state_eligible"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "INVALID_OBLIGATION_STATE", f"State {obligation.status} not eligible for recovery")
        checks["obligation_state_eligible"] = True
        
        # Check 6: Action Registry
        stmt = select(RecoveryActionDefinition).where(RecoveryActionDefinition.action_id == decision.action)
        action_def = (await db.execute(stmt)).scalar_one_or_none()
        if not action_def or not action_def.enabled:
            checks["action_registered"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "ACTION_UNAVAILABLE", f"Action {decision.action} is not registered or disabled")
        checks["action_registered"] = True
        
        # Check 7 & 10: Merchant policy & Amount boundary
        policy = await _get_active_policy(db)
        if not policy:
            checks["policy_allows_action"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "SYSTEM_VALIDATION_FAILED", "No active recovery policy found")
            
        allowed = policy.allowed_actions if isinstance(policy.allowed_actions, list) else json.loads(policy.allowed_actions)
        if decision.action not in allowed:
            checks["policy_allows_action"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "POLICY_ACTION_NOT_ALLOWED", f"Action {decision.action} not allowed by policy")
            
        if obligation.outstanding_amount > policy.max_autonomous_amount:
            checks["amount_within_limit"] = False
            if policy.require_human_above_amount:
                return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "REQUIRE_HUMAN_REVIEW", f"Amount {obligation.outstanding_amount} exceeds autonomous limit {policy.max_autonomous_amount}")
        checks["amount_within_limit"] = True
        checks["policy_allows_action"] = True
        
        # Check 8: Cooldown
        stmt = select(RecoveryExecution).where(
            RecoveryExecution.obligation_id == obligation.id
        ).order_by(desc(RecoveryExecution.created_at)).limit(1)
        last_exec = (await db.execute(stmt)).scalar_one_or_none()
        
        if last_exec:
            last_exec_time = last_exec.created_at
            if last_exec_time.tzinfo is None:
                last_exec_time = last_exec_time.replace(tzinfo=timezone.utc)
            time_since = (now_utc - last_exec_time).total_seconds()
            if time_since < policy.cooldown_seconds:
                checks["cooldown_satisfied"] = False
                return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "RECOVERY_COOLDOWN", f"Cooldown active. {time_since}s < {policy.cooldown_seconds}s")
        checks["cooldown_satisfied"] = True
        
        # Check 9: Duplicate active action
        stmt = select(RecoveryExecution).where(
            RecoveryExecution.obligation_id == obligation.id,
            RecoveryExecution.action == decision.action,
            RecoveryExecution.execution_status.in_(["AUTHORIZED_PENDING_EXECUTION", "EXECUTING"])
        )
        duplicate = (await db.execute(stmt)).first()
        if duplicate:
            checks["duplicate_action"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "DUPLICATE_ACTIVE_ACTION", f"An active {decision.action} already exists")
        checks["duplicate_action"] = True
        
        # Limit check
        stmt = select(sa.func.count(RecoveryExecution.id)).where(RecoveryExecution.obligation_id == obligation.id)
        exec_count = (await db.execute(stmt)).scalar_one()
        if exec_count >= policy.max_actions_per_obligation:
            checks["attempt_limit"] = False
            return await _record_evaluation(db, decision, obligation, checks, "BLOCK", "ATTEMPT_LIMIT_REACHED", f"Max actions {policy.max_actions_per_obligation} reached")
        checks["attempt_limit"] = True
        
        # If all checks pass
        return await _record_evaluation(db, decision, obligation, checks, "ALLOW", "AUTHORIZED", "Decision authorized by firewall")
        
    except Exception as e:
        # Fail closed on unexpected errors
        return await _record_evaluation(db, decision, None, checks, "BLOCK", "SYSTEM_VALIDATION_FAILED", str(e))

async def _record_evaluation(
    db: AsyncSession, 
    decision: RecoveryDecision, 
    obligation: FinancialObligation,
    checks: Dict[str, bool],
    result: str, 
    reason_code: str, 
    reason: str
) -> Dict[str, Any]:
    
    # 1. Update Decision Status
    decision.status = "APPROVED" if result == "ALLOW" else result
    
    expected_v = decision.state_version
    actual_v = obligation.state_version if obligation else -1
    
    # 2. Record Firewall Evaluation
    eval_record = FirewallEvaluation(
        decision_id=decision.id,
        state_version_expected=expected_v,
        state_version_actual=actual_v,
        checks=checks,
        result=result,
        reason_code=reason_code,
        reason=reason
    )
    db.add(eval_record)
    
    # 3. Create Execution Record ONLY if ALLOW
    if result == "ALLOW":
        idempotency_key = f"exec_{decision.id}"
        exec_record = RecoveryExecution(
            decision_id=decision.id,
            obligation_id=decision.obligation_id,
            action=decision.action,
            execution_status="AUTHORIZED_PENDING_EXECUTION",
            idempotency_key=idempotency_key,
            state_version_at_check=actual_v
        )
        db.add(exec_record)
        
    await db.commit()
    
    return {
        "decision_id": str(decision.id),
        "result": result,
        "reason_code": reason_code,
        "reason": reason,
        "checks": checks,
        "state_version_expected": expected_v,
        "state_version_actual": actual_v
    }

def _fail_closed(db: AsyncSession, decision_id: Any, reason_code: str, reason: str) -> Dict[str, Any]:
    # Pure fail-closed function for cases where decision doesn't exist or we can't write to it.
    return {
        "decision_id": str(decision_id),
        "result": "BLOCK",
        "reason_code": reason_code,
        "reason": reason,
        "checks": {},
        "state_version_expected": -1,
        "state_version_actual": -1
    }
