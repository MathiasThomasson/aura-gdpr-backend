from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit_log import AuditLog


async def log_event(db: AsyncSession, tenant_id: int, user_id: int | None, entity_type: str, entity_id: int | None, action: str, metadata: dict | None = None):
    # ensure metadata is minimal (no PII)
    safe_meta = metadata or {}
    al = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        action=action,
        metadata_json=safe_meta,
        meta=safe_meta,
    )
    db.add(al)
    await db.commit()
    await db.refresh(al)
    return al
