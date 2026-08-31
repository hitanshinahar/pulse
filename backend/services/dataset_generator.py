import random
import uuid
import math
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import RecoveryTrainingExample

DATASET_VERSION = 1

class SyntheticDataAssumptions:
    """
    Documented behavioral assumptions for the synthetic data generator.
    
    1. Base natural recovery (WAIT) varies continuously based on obligation_age.
    2. PAYMENT_LINK provides a heterogeneous treatment effect (uplift).
    3. The uplift depends smoothly on time since last failure and amount due, with interactions.
    4. Stochastic noise ensures the outcomes are not deterministic.
    5. Ground truth probabilities are isolated in `_metadata` to prevent leakage.
    """
    pass

def generate_context(seed: int, i: int) -> Dict[str, Any]:
    """Generates a random but realistic financial context."""
    rng = random.Random(seed + i)
    
    amount = rng.choice([500.0, 1500.0, 5000.0, 20000.0])
    # Apply some continuous variation to amount
    amount = round(amount * rng.uniform(0.8, 1.2), 2)
    
    historical_success_rate = rng.choice([0.1, 0.5, 0.9, None])
    time_since_last_failure_seconds = rng.randint(60, 7 * 24 * 3600) # 1 min to 7 days
    failure_category = rng.choice(['insufficient_funds', 'authentication_failed', 'do_not_honor', 'unknown'])
    attempt_count = rng.randint(1, 5)
    
    context_id = str(uuid.UUID(int=rng.getrandbits(128), version=4))
    
    return {
        "_metadata": {
            "context_id": context_id
        },
        "amount_due": amount,
        "outstanding_amount": amount,
        "obligation_age_seconds": time_since_last_failure_seconds + 3600,
        "obligation_state": "RECOVERY_ELIGIBLE",
        "attempt_count": attempt_count,
        "failed_attempt_count": attempt_count,
        "captured_attempt_count": 0,
        "last_attempt_age_seconds": time_since_last_failure_seconds,
        "time_since_last_failure_seconds": time_since_last_failure_seconds,
        "failure_category": failure_category,
        "failure_code": f"code_{rng.randint(100, 999)}",
        "failure_reason": "synthetic reason",
        "payment_method": rng.choice(['upi', 'card', 'netbanking']),
        "previous_obligation_count": rng.randint(0, 10),
        "previous_success_count": rng.randint(0, 5),
        "previous_failure_count": rng.randint(0, 5),
        "historical_success_rate": historical_success_rate,
        "historical_average_amount": round(amount * rng.uniform(0.5, 1.5), 2),
        "hour_of_day": rng.randint(0, 23),
        "day_of_week": rng.randint(0, 6)
    }

def calculate_outcomes(context: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Calculates potential outcomes using a probabilistic data-generating process."""
    
    # Base WAIT probability (logistic function basis)
    # Log-odds scale
    logit_wait = -2.0 # Base ~ 11%
    
    if context['failure_category'] == 'insufficient_funds':
        logit_wait += 1.0 # Higher natural recovery
        
    # Decay natural recovery as time passes
    days_since = context['time_since_last_failure_seconds'] / 86400
    logit_wait -= (days_since * 0.1)
    
    if context['historical_success_rate']:
        logit_wait += (context['historical_success_rate'] - 0.5) * 2.0
        
    p_wait = 1.0 / (1.0 + math.exp(-logit_wait))
    
    # Treatment effect (Uplift)
    # Log-odds boost for PAYMENT_LINK
    treatment_effect = 0.5 # Base uplift
    
    if context['failure_category'] == 'authentication_failed':
        treatment_effect += 1.5
        
    # Interaction: Small amounts have higher uplift
    if context['amount_due'] < 2000:
        treatment_effect += 0.8
    elif context['amount_due'] > 10000:
        treatment_effect -= 0.5
        
    # Decay treatment effect if we wait too long
    treatment_effect -= (days_since * 0.15)
    
    logit_link = logit_wait + treatment_effect
    p_link = 1.0 / (1.0 + math.exp(-logit_link))
    
    return {
        "p_wait": p_wait,
        "p_link": p_link,
        "WAIT": 1 if rng.random() < p_wait else 0,
        "PAYMENT_LINK": 1 if rng.random() < p_link else 0
    }

async def generate_synthetic_dataset(db: AsyncSession, seed: int = 42, num_contexts: int = 20000):
    """
    Generates potential outcomes for candidate actions.
    Produces 2 rows per context (one for WAIT, one for PAYMENT_LINK).
    """
    
    examples = []
    rng = random.Random(seed)
    
    for i in range(num_contexts):
        context = generate_context(seed, i)
        outcomes = calculate_outcomes(context, rng)
        
        # Inject ground truth metadata for the evaluator. 
        # MUST NOT be used by the ML model.
        context["_metadata"]["p_wait"] = outcomes["p_wait"]
        context["_metadata"]["p_link"] = outcomes["p_link"]
        context["_metadata"]["true_probability_uplift"] = outcomes["p_link"] - outcomes["p_wait"]
        context["_metadata"]["Y_wait"] = outcomes["WAIT"]
        context["_metadata"]["Y_link"] = outcomes["PAYMENT_LINK"]
        context["_metadata"]["observed_potential_outcome_difference"] = outcomes["PAYMENT_LINK"] - outcomes["WAIT"]
        
        for action in ["WAIT", "PAYMENT_LINK"]:
            examples.append(
                RecoveryTrainingExample(
                    dataset_version=DATASET_VERSION,
                    source='synthetic',
                    features=context,
                    candidate_action=action,
                    outcome=outcomes[action]
                )
            )
            
    # Bulk insert
    db.add_all(examples)
    await db.commit()
    return len(examples)
