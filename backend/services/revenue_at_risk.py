from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from backend.models import FinancialObligation

async def get_revenue_at_risk(db: AsyncSession) -> List[FinancialObligation]:
    """
    Identifies obligations that have outstanding amount > 0,
    valid financial state (UNRESOLVED, RECOVERY_ELIGIBLE),
    and are not already satisfied or closed.
    """
    stmt = select(FinancialObligation).where(
        FinancialObligation.outstanding_amount > 0,
        FinancialObligation.status.in_(["UNRESOLVED", "RECOVERY_ELIGIBLE"])
    ).order_by(FinancialObligation.updated_at.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()
