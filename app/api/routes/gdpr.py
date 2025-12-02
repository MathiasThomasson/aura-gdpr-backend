from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.deps import CurrentContext, current_context
from app.core.config import settings
from app.db.database import get_db
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.processing_activity import ProcessingActivity
from app.db.models.refresh_token import RefreshToken
from app.db.models.task import Task
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.knowledge_document import KnowledgeDocument
from app.db.models.knowledge_chunk import KnowledgeChunk
from app.services.rag_service import delete_rag_for_tenant
from app.repositories.document_repository import delete_document, list_documents
from app.repositories.task_repository import delete_task, list_tasks

router = APIRouter(prefix="/api/gdpr", tags=["GDPR"])


async def _anonymize_email(email: str) -> str:
    return f"deleted_user_{uuid.uuid4().hex[:12]}@anonymized.local"


@router.get("/export/user/{user_id}")
async def export_user(user_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    user = await db.get(User, user_id)
    if not user or user.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    tasks = await list_tasks(db, ctx.tenant_id, limit=1000, offset=0)
    pas = (await db.execute(select(ProcessingActivity).where(ProcessingActivity.tenant_id == ctx.tenant_id))).scalars().all()
    docs = await list_documents(db, ctx.tenant_id)
    audits = (await db.execute(select(AuditLog).where(AuditLog.tenant_id == ctx.tenant_id))).scalars().all()
    rag_docs = (await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == ctx.tenant_id))).scalars().all()

    return {
        "user": {"id": user.id, "email": user.email, "role": user.role, "tenant_id": user.tenant_id},
        "tasks": [{"id": t.id, "title": t.title, "status": t.status, "category": t.category, "due_date": t.due_date} for t in tasks],
        "processing_activities": [{"id": p.id, "name": p.name, "description": p.description} for p in pas],
        "documents": [
            {"id": d.id, "title": d.title, "category": d.category, "version": getattr(d, "version", getattr(d, "current_version", None))}
            for d in docs
        ],
        "audit_logs": [
            {"id": a.id, "entity_type": a.entity_type, "entity_id": a.entity_id, "action": a.action, "timestamp": getattr(a, "created_at", None)}
            for a in audits
        ],
        "rag_documents": [{"id": d.id, "title": d.title, "source": d.source, "language": d.language} for d in rag_docs],
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/export/tenant/{tenant_id}")
async def export_tenant(tenant_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    if tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or not getattr(tenant, "is_active", True):
        raise HTTPException(status_code=404, detail="Tenant not found")
    users = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.tenant_id == tenant_id, Task.deleted_at.is_(None)))).scalars().all()
    pas = (await db.execute(select(ProcessingActivity).where(ProcessingActivity.tenant_id == tenant_id))).scalars().all()
    docs = (await db.execute(select(Document).where(Document.tenant_id == tenant_id, Document.deleted_at.is_(None)))).scalars().all()
    audits = (await db.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id))).scalars().all()
    rag_docs = (await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id))).scalars().all()

    return {
        "tenant": {"id": tenant.id, "name": tenant.name, "created_at": tenant.created_at},
        "users": [{"id": u.id, "email": u.email, "role": u.role} for u in users],
        "tasks": [{"id": t.id, "title": t.title, "status": t.status, "category": t.category, "due_date": t.due_date} for t in tasks],
        "processing_activities": [{"id": p.id, "name": p.name, "description": p.description} for p in pas],
        "documents": [
            {"id": d.id, "title": d.title, "category": d.category, "version": getattr(d, "version", getattr(d, "current_version", None))}
            for d in docs
        ],
        "audit_logs": [
            {"id": a.id, "entity_type": a.entity_type, "entity_id": a.entity_id, "action": a.action, "timestamp": getattr(a, "created_at", None)}
            for a in audits
        ],
        "rag_documents": [{"id": d.id, "title": d.title, "source": d.source, "language": d.language} for d in rag_docs],
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/delete/user/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    user = await db.get(User, user_id)
    if not user or user.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    anonymized = await _anonymize_email(user.email)
    user.email = anonymized
    # revoke refresh tokens
    await db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True, revoked_reason="dsar_user_delete"))
    # soft-delete tasks assigned to this user
    now = datetime.utcnow()
    await db.execute(update(Task).where(Task.tenant_id == ctx.tenant_id, Task.assigned_to_user_id == user.id).values(deleted_at=now))
    db.add(user)
    await db.commit()
    await log_event(db, ctx.tenant_id, ctx.user.id, "dsar", user.id, "user_anonymized", {"target_user": user.id})
    return {"ok": True, "anonymized": True}


@router.post("/delete/tenant/{tenant_id}")
async def delete_tenant(tenant_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    if tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    now = datetime.utcnow()
    tenant = await db.get(Tenant, tenant_id)
    # anonymize all users
    users = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
    for u in users:
        u.email = await _anonymize_email(u.email)
        db.add(u)
    await db.execute(update(RefreshToken).where(RefreshToken.tenant_id == tenant_id).values(revoked=True, revoked_reason="dsar_tenant_delete"))
    await db.execute(update(Task).where(Task.tenant_id == tenant_id).values(deleted_at=now))
    await db.execute(update(Document).where(Document.tenant_id == tenant_id).values(deleted_at=now))
    # hard delete rag docs/chunks for tenant
    await delete_rag_for_tenant(db, tenant_id)
    if tenant:
        tenant.is_active = False
        db.add(tenant)
    await db.commit()
    await log_event(db, ctx.tenant_id, ctx.user.id, "dsar", tenant_id, "tenant_anonymized", {"tenant": tenant_id})
    return {"ok": True}
