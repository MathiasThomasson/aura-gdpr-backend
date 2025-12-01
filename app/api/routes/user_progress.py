from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.user_progress import UserProgressOut, UserProgressUpdate
from app.services.user_progress_service import get_progress, patch_progress

router = APIRouter(prefix="/api/user-progress", tags=["User Progress"])


@router.get("", response_model=UserProgressOut, summary="Get user progress", description="Return onboarding checklist state for current user and tenant.")
async def read_user_progress(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    progress = await get_progress(db, ctx.tenant_id, ctx.user.id)
    return UserProgressOut.model_validate(progress)


@router.patch("", response_model=UserProgressOut, summary="Update user progress", description="Patch onboarding checklist state for current user and tenant.")
async def update_user_progress(
    payload: UserProgressUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    progress = await patch_progress(db, ctx.tenant_id, ctx.user.id, payload)
    return UserProgressOut.model_validate(progress)
