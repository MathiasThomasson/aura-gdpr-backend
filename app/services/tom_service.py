from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tom import TOM
from app.schemas.tom import TOMCreate, TOMUpdate
from app.services.simple_crud_service import SimpleCRUDService

service = SimpleCRUDService[TOM](TOM)


async def list_toms(db: AsyncSession, tenant_id: int):
    return await service.list(db, tenant_id)


async def create_tom(db: AsyncSession, tenant_id: int, payload: TOMCreate):
    return await service.create(db, tenant_id, payload.model_dump(exclude_unset=True))


async def get_tom(db: AsyncSession, tenant_id: int, item_id: int):
    return await service.get_or_404(db, tenant_id, item_id)


async def update_tom(db: AsyncSession, tenant_id: int, item_id: int, payload: TOMUpdate):
    item = await service.get_or_404(db, tenant_id, item_id)
    return await service.update(db, item, payload.model_dump(exclude_unset=True))


async def delete_tom(db: AsyncSession, tenant_id: int, item_id: int):
    item = await service.get_or_404(db, tenant_id, item_id)
    await service.delete(db, item)
    return {"ok": True}
