from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.policy import PolicyCreate, PolicyOut, PolicyUpdate
from app.services.policy_service import create_policy, delete_policy, get_policy, list_policies, update_policy

router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("", response_model=list[PolicyOut], summary="List policies")
async def list_policy_items(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await list_policies(db, ctx.tenant_id)


@router.post("", response_model=PolicyOut, status_code=201, summary="Create policy")
async def create_policy_item(
    payload: PolicyCreate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await create_policy(db, ctx.tenant_id, payload)


@router.get("/{policy_id}", response_model=PolicyOut, summary="Get policy")
async def get_policy_item(
    policy_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await get_policy(db, ctx.tenant_id, policy_id)


@router.patch("/{policy_id}", response_model=PolicyOut, summary="Update policy")
async def update_policy_item(
    policy_id: int, payload: PolicyUpdate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await update_policy(db, ctx.tenant_id, policy_id, payload)


@router.delete("/{policy_id}", summary="Delete policy")
async def delete_policy_item(
    policy_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await delete_policy(db, ctx.tenant_id, policy_id)
