from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.models import RecoveryActionDefinition

async def seed_action_registry(db: AsyncSession):
    """Seed the Recovery Action Registry with default capabilities."""
    actions = [
        RecoveryActionDefinition(
            action_id="WAIT",
            name="Wait",
            description="Do nothing and allow natural recovery or retries to occur.",
            enabled=True,
            requires_outstanding_balance=True,
            requires_customer_information=False,
            external_provider=None,
            capability="noop",
            risk_level="none"
        ),
        RecoveryActionDefinition(
            action_id="PAYMENT_LINK",
            name="Send Payment Link",
            description="Generate a Razorpay Payment Link for the outstanding amount.",
            enabled=True,
            requires_outstanding_balance=True,
            requires_customer_information=True, # Requires contact info in real scenarios
            external_provider="razorpay",
            capability="payment_link_generation",
            risk_level="low"
        )
    ]
    
    for action in actions:
        stmt = select(RecoveryActionDefinition).where(RecoveryActionDefinition.action_id == action.action_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if not existing:
            db.add(action)
    
    await db.commit()
