from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.notification import NotificationListResponse, NotificationRead
from app.services.notification_service import list_notifications, mark_all_read, mark_notification_read

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    only_unread: bool = False,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    items, total = await list_notifications(db, ctx.tenant_id, ctx.user.id, ctx.role, only_unread)
    return NotificationListResponse(items=items, total=total)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    notif = await mark_notification_read(db, ctx.tenant_id, ctx.user.id, ctx.role, notification_id)
    return notif


@router.post("/mark-all-read")
async def mark_all(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    updated = await mark_all_read(db, ctx.tenant_id, ctx.user.id, ctx.role)
    return {"updated": updated}
