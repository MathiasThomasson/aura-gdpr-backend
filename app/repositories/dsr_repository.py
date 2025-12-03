from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dsr import DataSubjectRequest


async def get_dsr_by_id(db: AsyncSession, tenant_id: int, dsr_id: int) -> Optional[DataSubjectRequest]:
    result = await db.execute(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == dsr_id,
            DataSubjectRequest.tenant_id == tenant_id,
            DataSubjectRequest.deleted_at.is_(None),
        )
    )
    return result.scalars().first()
