from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyUpdate
from app.services.simple_crud_service import SimpleCRUDService

service = SimpleCRUDService[Policy](Policy)


async def list_policies(db: AsyncSession, tenant_id: int):
    return await service.list(db, tenant_id)


async def create_policy(db: AsyncSession, tenant_id: int, payload: PolicyCreate):
    return await service.create(db, tenant_id, payload.model_dump(exclude_unset=True))


async def get_policy(db: AsyncSession, tenant_id: int, policy_id: int):
    return await service.get_or_404(db, tenant_id, policy_id)


async def update_policy(db: AsyncSession, tenant_id: int, policy_id: int, payload: PolicyUpdate):
    policy = await service.get_or_404(db, tenant_id, policy_id)
    return await service.update(db, policy, payload.model_dump(exclude_unset=True))


async def delete_policy(db: AsyncSession, tenant_id: int, policy_id: int):
    policy = await service.get_or_404(db, tenant_id, policy_id)
    await service.delete(db, policy)
    return {"ok": True}
