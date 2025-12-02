from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ropa import ROPA
from app.schemas.ropa import ROPARecordCreate, ROPARecordUpdate
from app.services.simple_crud_service import SimpleCRUDService

service = SimpleCRUDService[ROPA](ROPA)


async def list_ropa(db: AsyncSession, tenant_id: int):
    return await service.list(db, tenant_id)


async def create_ropa(db: AsyncSession, tenant_id: int, payload: ROPARecordCreate):
    return await service.create(db, tenant_id, payload.model_dump(exclude_unset=True))


async def get_ropa(db: AsyncSession, tenant_id: int, item_id: int):
    return await service.get_or_404(db, tenant_id, item_id)


async def update_ropa(db: AsyncSession, tenant_id: int, item_id: int, payload: ROPARecordUpdate):
    item = await service.get_or_404(db, tenant_id, item_id)
    return await service.update(db, item, payload.model_dump(exclude_unset=True))


async def delete_ropa(db: AsyncSession, tenant_id: int, item_id: int):
    item = await service.get_or_404(db, tenant_id, item_id)
    await service.delete(db, item)
    return {"ok": True}
