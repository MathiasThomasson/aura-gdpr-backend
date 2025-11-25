from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.db.models.audit_log import AuditLog
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/audit_logs", tags=["AuditLogs"])


@router.get("/")
async def list_audit_logs(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user), limit: int = 50, offset: int = 0, entity_type: str | None = None, action: str | None = None, user_id: int | None = None):
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    q = select(AuditLog).where(AuditLog.tenant_id == current_user.tenant_id)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if action:
        q = q.where(AuditLog.action == action)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    q = q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    items = result.scalars().all()
    return items
