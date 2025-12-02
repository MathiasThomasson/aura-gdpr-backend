from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.cookie import Cookie
from app.schemas.cookie import CookieCreate, CookieUpdate
from app.services.simple_crud_service import SimpleCRUDService

service = SimpleCRUDService[Cookie](Cookie)


async def list_cookies(db: AsyncSession, tenant_id: int):
    return await service.list(db, tenant_id)


async def create_cookie(db: AsyncSession, tenant_id: int, payload: CookieCreate):
    return await service.create(db, tenant_id, payload.model_dump(exclude_unset=True))


async def get_cookie(db: AsyncSession, tenant_id: int, item_id: int):
    return await service.get_or_404(db, tenant_id, item_id)


async def update_cookie(db: AsyncSession, tenant_id: int, item_id: int, payload: CookieUpdate):
    item = await service.get_or_404(db, tenant_id, item_id)
    return await service.update(db, item, payload.model_dump(exclude_unset=True))


async def delete_cookie(db: AsyncSession, tenant_id: int, item_id: int):
    item = await service.get_or_404(db, tenant_id, item_id)
    await service.delete(db, item)
    return {"ok": True}
