from datetime import datetime
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


ModelType = TypeVar("ModelType")


class TenantCRUDRepository(Generic[ModelType]):
    """Generic repository for simple tenant-scoped CRUD resources."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def list(self, db: AsyncSession, tenant_id: int) -> list[ModelType]:
        res = await db.execute(
            select(self.model).where(self.model.tenant_id == tenant_id).order_by(getattr(self.model, "created_at").desc())
        )
        return res.scalars().all()

    async def get(self, db: AsyncSession, tenant_id: int, item_id: int) -> Optional[ModelType]:
        return await db.scalar(
            select(self.model).where(self.model.id == item_id, self.model.tenant_id == tenant_id)  # type: ignore[attr-defined]
        )

    async def create(self, db: AsyncSession, tenant_id: int, data: dict) -> ModelType:
        instance = self.model(tenant_id=tenant_id, **data)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, instance: ModelType, data: dict) -> ModelType:
        for key, value in data.items():
            setattr(instance, key, value)
        if hasattr(instance, "updated_at"):
            setattr(instance, "updated_at", datetime.utcnow())
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    async def delete(self, db: AsyncSession, instance: ModelType) -> None:
        await db.delete(instance)
        await db.commit()
