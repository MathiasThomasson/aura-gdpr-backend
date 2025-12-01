from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_progress import UserProgress
from app.schemas.user_progress import UserProgressUpdate


async def get_progress(db: AsyncSession, tenant_id: int, user_id: int) -> UserProgress:
    progress = await db.scalar(select(UserProgress).where(UserProgress.tenant_id == tenant_id, UserProgress.user_id == user_id))
    if progress:
        return progress
    progress = UserProgress(tenant_id=tenant_id, user_id=user_id)
    db.add(progress)
    await db.commit()
    await db.refresh(progress)
    return progress


async def patch_progress(db: AsyncSession, tenant_id: int, user_id: int, payload: UserProgressUpdate) -> UserProgress:
    progress = await get_progress(db, tenant_id, user_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(progress, field, value)
    db.add(progress)
    await db.commit()
    await db.refresh(progress)
    return progress
