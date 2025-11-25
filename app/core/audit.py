from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit_log import AuditLog


async def log_event(db: AsyncSession, tenant_id: int, user_id: int | None, entity_type: str, entity_id: int | None, action: str, metadata: dict | None = None):
    al = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        meta=metadata,
    )
    db.add(al)
    await db.commit()
    await db.refresh(al)
    return al
