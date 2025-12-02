from typing import Generic, TypeVar

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.simple_crud_repository import TenantCRUDRepository

ModelType = TypeVar("ModelType")


class SimpleCRUDService(Generic[ModelType]):
    """Thin service wrapper around the tenant-scoped CRUD repository."""

    def __init__(self, model: type[ModelType]):
        self.repo = TenantCRUDRepository[ModelType](model)

    async def list(self, db: AsyncSession, tenant_id: int) -> list[ModelType]:
        return await self.repo.list(db, tenant_id)

    async def get_or_404(self, db: AsyncSession, tenant_id: int, item_id: int) -> ModelType:
        item = await self.repo.get(db, tenant_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item

    async def create(self, db: AsyncSession, tenant_id: int, data: dict) -> ModelType:
        return await self.repo.create(db, tenant_id, data)

    async def update(self, db: AsyncSession, item: ModelType, data: dict) -> ModelType:
        return await self.repo.update(db, item, data)

    async def delete(self, db: AsyncSession, item: ModelType) -> None:
        await self.repo.delete(db, item)
