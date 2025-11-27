from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.processing_activity import ProcessingActivity
from app.repositories.processing_activity_repository import (
    create_processing_activity as repo_create,
    delete_processing_activity as repo_delete,
    get_processing_activity as repo_get,
    list_processing_activities as repo_list,
    save_processing_activity as repo_save,
)


async def create_processing_activity(db: AsyncSession, tenant_id: int, name: str, description: Optional[str]) -> ProcessingActivity:
    return await repo_create(db, tenant_id, name, description)


async def list_processing_activities(db: AsyncSession, tenant_id: int, limit: int, offset: int):
    return await repo_list(db, tenant_id, limit, offset)


async def get_processing_activity(db: AsyncSession, tenant_id: int, pa_id: int) -> ProcessingActivity:
    pa = await repo_get(db, tenant_id, pa_id)
    if not pa:
        raise HTTPException(status_code=404, detail="ProcessingActivity not found")
    return pa


async def update_processing_activity(db: AsyncSession, tenant_id: int, pa_id: int, name: Optional[str], description: Optional[str]):
    pa = await get_processing_activity(db, tenant_id, pa_id)
    if name is not None:
        pa.name = name
    if description is not None:
        pa.description = description
    return await repo_save(db, pa)


async def delete_processing_activity(db: AsyncSession, tenant_id: int, pa_id: int):
    pa = await get_processing_activity(db, tenant_id, pa_id)
    await repo_delete(db, pa)
    return pa
