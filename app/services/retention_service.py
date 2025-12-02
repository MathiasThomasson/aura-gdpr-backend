from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.audit_log import AuditLog
from app.db.models.refresh_token import RefreshToken
from app.db.models.document import Document
from app.db.models.task import Task
from app.db.models.knowledge_document import KnowledgeDocument
from app.db.models.knowledge_chunk import KnowledgeChunk
from app.db.models.knowledge_embedding import KnowledgeEmbedding


async def apply_retention(db: AsyncSession) -> dict:
    """Retention cleanup stub; can be scheduled externally."""
    now = datetime.now(timezone.utc)
    summary = {}

    # Tokens retention
    cutoff_tokens = now - timedelta(days=int(settings.RETENTION_DAYS_TOKENS or 30))
    res = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < cutoff_tokens)
    )
    summary["refresh_tokens_deleted"] = res.rowcount or 0

    # Audit logs retention
    cutoff_logs = now - timedelta(days=int(settings.RETENTION_DAYS_LOGS or 365))
    res = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff_logs))
    summary["audit_logs_deleted"] = res.rowcount or 0

    # Documents retention (soft delete purge)
    cutoff_docs = now - timedelta(days=int(settings.RETENTION_DAYS_DOCUMENTS or 365))
    res = await db.execute(
        delete(Document).where(Document.deleted_at.isnot(None), Document.deleted_at < cutoff_docs)
    )
    summary["documents_deleted"] = res.rowcount or 0

    # RAG retention: purge deleted docs/chunks/embeddings older than cutoff
    cutoff_rag = now - timedelta(days=int(settings.RETENTION_DAYS_RAG or 365))
    await db.execute(delete(KnowledgeEmbedding).where(KnowledgeEmbedding.created_at < cutoff_rag))
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.created_at < cutoff_rag))
    await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.created_at < cutoff_rag))

    await db.commit()
    return summary
