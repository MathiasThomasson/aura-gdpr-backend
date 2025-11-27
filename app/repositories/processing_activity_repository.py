from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.processing_activity import ProcessingActivity


async def create_processing_activity(
    db: AsyncSession, tenant_id: int, name: str, description: Optional[str]
) -> ProcessingActivity:
    pa = ProcessingActivity(tenant_id=tenant_id, name=name, description=description)
    db.add(pa)
    await db.commit()
    await db.refresh(pa)
    return pa


async def list_processing_activities(db: AsyncSession, tenant_id: int, limit: int, offset: int) -> List[ProcessingActivity]:
    res = await db.execute(
        select(ProcessingActivity)
        .where(ProcessingActivity.tenant_id == tenant_id)
        .order_by(ProcessingActivity.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return res.scalars().all()


async def get_processing_activity(db: AsyncSession, tenant_id: int, pa_id: int) -> Optional[ProcessingActivity]:
    res = await db.execute(
        select(ProcessingActivity).where(ProcessingActivity.id == pa_id, ProcessingActivity.tenant_id == tenant_id)
    )
    return res.scalars().first()


async def save_processing_activity(db: AsyncSession, pa: ProcessingActivity) -> ProcessingActivity:
    db.add(pa)
    await db.commit()
    await db.refresh(pa)
    return pa


async def delete_processing_activity(db: AsyncSession, pa: ProcessingActivity) -> None:
    await db.delete(pa)
    await db.commit()
