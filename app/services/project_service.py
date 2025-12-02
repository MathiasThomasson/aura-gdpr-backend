from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.simple_crud_service import SimpleCRUDService

service = SimpleCRUDService[Project](Project)


async def list_projects(db: AsyncSession, tenant_id: int):
    return await service.list(db, tenant_id)


async def create_project(db: AsyncSession, tenant_id: int, payload: ProjectCreate):
    return await service.create(db, tenant_id, payload.model_dump(exclude_unset=True))


async def get_project(db: AsyncSession, tenant_id: int, item_id: int):
    return await service.get_or_404(db, tenant_id, item_id)


async def update_project(db: AsyncSession, tenant_id: int, item_id: int, payload: ProjectUpdate):
    item = await service.get_or_404(db, tenant_id, item_id)
    return await service.update(db, item, payload.model_dump(exclude_unset=True))


async def delete_project(db: AsyncSession, tenant_id: int, item_id: int):
    item = await service.get_or_404(db, tenant_id, item_id)
    await service.delete(db, item)
    return {"ok": True}
