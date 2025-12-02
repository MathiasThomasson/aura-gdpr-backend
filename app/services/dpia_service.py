from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dpia import DPIA
from app.schemas.dpia import DPIACreate, DPIAUpdate
from app.services.simple_crud_service import SimpleCRUDService

service = SimpleCRUDService[DPIA](DPIA)


async def list_dpia(db: AsyncSession, tenant_id: int):
    return await service.list(db, tenant_id)


async def create_dpia(db: AsyncSession, tenant_id: int, payload: DPIACreate):
    return await service.create(db, tenant_id, payload.model_dump(exclude_unset=True))


async def get_dpia(db: AsyncSession, tenant_id: int, item_id: int):
    return await service.get_or_404(db, tenant_id, item_id)


async def update_dpia(db: AsyncSession, tenant_id: int, item_id: int, payload: DPIAUpdate):
    item = await service.get_or_404(db, tenant_id, item_id)
    return await service.update(db, item, payload.model_dump(exclude_unset=True))


async def delete_dpia(db: AsyncSession, tenant_id: int, item_id: int):
    item = await service.get_or_404(db, tenant_id, item_id)
    await service.delete(db, item)
    return {"ok": True}
