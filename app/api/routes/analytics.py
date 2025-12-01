from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.analytics import AnalyticsEventCreate, AnalyticsEventOut
from app.services.analytics_service import record_event

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.post("/event", response_model=AnalyticsEventOut, status_code=201, summary="Record analytics event", description="Record a GDPR-safe analytics event for the current user and tenant.")
async def create_event(
    payload: AnalyticsEventCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    event = await record_event(db, ctx.tenant_id, ctx.user.id, payload.event_name)
    return AnalyticsEventOut.model_validate(event)
