from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.onboarding import OnboardingStateOut, OnboardingStateUpdate
from app.services.onboarding_service import get_onboarding_state, update_onboarding_state

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


@router.get("/state", response_model=OnboardingStateOut, summary="Get onboarding state", description="Return onboarding state for the current user and tenant.")
async def read_onboarding_state(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    state = await get_onboarding_state(db, ctx.tenant_id, ctx.user.id)
    return OnboardingStateOut.model_validate(state)


@router.patch("/state", response_model=OnboardingStateOut, summary="Update onboarding state", description="Update onboarding progress for the current user and tenant.")
async def patch_onboarding_state(
    payload: OnboardingStateUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    state = await update_onboarding_state(db, ctx.tenant_id, ctx.user.id, payload.onboarding_completed, payload.onboarding_step)
    return OnboardingStateOut.model_validate(state)
