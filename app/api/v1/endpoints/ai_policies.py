from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.core.roles import Role
from app.db.database import get_db
from app.schemas.ai_policies import PolicyGenerateRequest, PolicyGenerateResponse
from app.services.ai_policy_service import generate_policy

router = APIRouter(prefix="/api/ai/policies", tags=["AI Policies"])


def _assert_policy_role(ctx: CurrentContext):
    if ctx.role not in {Role.OWNER.value, Role.ADMIN.value, Role.EDITOR.value, Role.VIEWER.value}:
        raise HTTPException(status_code=403, detail="Insufficient privileges")


@router.post("/generate", response_model=PolicyGenerateResponse)
async def generate(
    payload: PolicyGenerateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    _assert_policy_role(ctx)
    # db currently unused but kept for future audit/logging hooks
    return await generate_policy(ctx.tenant_id, payload)
