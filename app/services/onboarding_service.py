from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.onboarding import OnboardingState


async def get_onboarding_state(db: AsyncSession, tenant_id: int, user_id: int) -> OnboardingState:
    existing = await db.scalar(
        select(OnboardingState).where(OnboardingState.tenant_id == tenant_id, OnboardingState.user_id == user_id)
    )
    if existing:
        return existing
    state = OnboardingState(tenant_id=tenant_id, user_id=user_id, onboarding_completed=False, onboarding_step=0)
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return state


async def update_onboarding_state(
    db: AsyncSession, tenant_id: int, user_id: int, completed: bool | None, step: int | None
) -> OnboardingState:
    state = await get_onboarding_state(db, tenant_id, user_id)
    if completed is not None:
        state.onboarding_completed = completed
    if step is not None:
        state.onboarding_step = step
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return state
