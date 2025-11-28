from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import (
    Document,
    DocumentAISummary,
    DocumentTag,
    DocumentTagLink,
    DocumentVersion,
)
from app.schemas.document import (
    DocumentAISummaryCreate,
    DocumentAISummaryRead,
    DocumentCreate,
    DocumentListResponse,
    DocumentRead,
    DocumentTagRead,
    DocumentUpdate,
    DocumentVersionCreate,
    DocumentVersionRead,
)


async def _get_document(db: AsyncSession, tenant_id: int, doc_id: int) -> Document:
    res = await db.execute(
        select(Document).where(
            and_(Document.id == doc_id, Document.tenant_id == tenant_id, Document.deleted_at.is_(None))
        )
    )
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


async def _ensure_tags(db: AsyncSession, tenant_id: int, tag_names: List[str]) -> List[DocumentTag]:
    tags: List[DocumentTag] = []
    for name in tag_names:
        res = await db.execute(
            select(DocumentTag).where(DocumentTag.tenant_id == tenant_id, func.lower(DocumentTag.name) == name.lower())
        )
        tag = res.scalars().first()
        if not tag:
            tag = DocumentTag(tenant_id=tenant_id, name=name)
            db.add(tag)
            await db.flush()
        tags.append(tag)
    return tags


def _to_tag_read(link: DocumentTagLink) -> DocumentTagRead:
    return DocumentTagRead(id=link.tag.id, name=link.tag.name)


def _to_document_read(doc: Document) -> DocumentRead:
    tags = []
    for link in doc.tags or []:
        if link.tag:
            tags.append(_to_tag_read(link))
    return DocumentRead(
        id=doc.id,
        title=doc.title,
        category=doc.category,
        status=doc.status,
        current_version=doc.current_version,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        tags=tags,
    )


def _to_version_read(v: DocumentVersion) -> DocumentVersionRead:
    return DocumentVersionRead(
        id=v.id,
        version_number=v.version_number,
        file_name=v.file_name,
        mime_type=v.mime_type,
        size_bytes=v.size_bytes,
        created_at=v.created_at,
    )


def _to_summary_read(s: DocumentAISummary) -> DocumentAISummaryRead:
    return DocumentAISummaryRead(
        id=s.id,
        document_id=s.document_id,
        version_id=s.version_id,
        language=s.language,
        model_name=s.model_name,
        summary_text=s.summary_text,
        created_at=s.created_at,
    )


async def list_documents(
    db: AsyncSession,
    tenant_id: int,
    q: Optional[str],
    category: Optional[str],
    status: Optional[str],
    tag: Optional[str],
    skip: int,
    limit: int,
) -> DocumentListResponse:
    base = select(Document).where(Document.tenant_id == tenant_id, Document.deleted_at.is_(None))
    if q:
        base = base.where(Document.title.ilike(f"%{q}%"))
    if category:
        base = base.where(Document.category == category)
    if status:
        base = base.where(Document.status == status)
    if tag:
        base = base.join(DocumentTagLink).join(DocumentTag).where(DocumentTag.name == tag)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    res = await db.execute(base.order_by(Document.id.desc()).offset(skip).limit(limit))
    docs = res.scalars().unique().all()
    return DocumentListResponse(items=[_to_document_read(d) for d in docs], total=total)


async def create_document(
    db: AsyncSession, tenant_id: int, user_id: int, payload: DocumentCreate
) -> DocumentRead:
    doc = Document(
        tenant_id=tenant_id,
        title=payload.title,
        category=payload.category,
        status=payload.status or "active",
        created_by_id=user_id,
    )
    db.add(doc)
    await db.flush()

    if payload.tags:
        tags = await _ensure_tags(db, tenant_id, payload.tags)
        for t in tags:
            db.add(DocumentTagLink(document_id=doc.id, tag_id=t.id))

    await db.commit()
    await db.refresh(doc)
    return _to_document_read(doc)


async def get_document(db: AsyncSession, tenant_id: int, doc_id: int) -> DocumentRead:
    doc = await _get_document(db, tenant_id, doc_id)
    return _to_document_read(doc)


async def update_document(
    db: AsyncSession, tenant_id: int, doc_id: int, payload: DocumentUpdate
) -> DocumentRead:
    doc = await _get_document(db, tenant_id, doc_id)
    if payload.title is not None:
        doc.title = payload.title
    if payload.category is not None:
        doc.category = payload.category
    if payload.status is not None:
        doc.status = payload.status

    if payload.tags is not None:
        tags = await _ensure_tags(db, tenant_id, payload.tags or [])
        existing_links = {link.tag_id: link for link in doc.tags or []}
        desired_ids = {t.id for t in tags}
        for link in list(doc.tags or []):
            if link.tag_id not in desired_ids:
                await db.delete(link)
        for t in tags:
            if t.id not in existing_links:
                db.add(DocumentTagLink(document_id=doc.id, tag_id=t.id))

    await db.commit()
    await db.refresh(doc)
    return _to_document_read(doc)


async def delete_document(db: AsyncSession, tenant_id: int, doc_id: int) -> None:
    doc = await _get_document(db, tenant_id, doc_id)
    doc.deleted_at = datetime.utcnow()
    await db.commit()


async def list_versions(db: AsyncSession, tenant_id: int, doc_id: int) -> List[DocumentVersionRead]:
    await _get_document(db, tenant_id, doc_id)
    res = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id).order_by(DocumentVersion.version_number.desc())
    )
    versions = res.scalars().all()
    return [_to_version_read(v) for v in versions]


async def add_version(
    db: AsyncSession, tenant_id: int, doc_id: int, user_id: int, payload: DocumentVersionCreate
) -> DocumentVersionRead:
    doc = await _get_document(db, tenant_id, doc_id)
    res = await db.execute(select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(DocumentVersion.document_id == doc_id))
    next_version = (res.scalar_one() or 0) + 1

    version = DocumentVersion(
        document_id=doc.id,
        version_number=next_version,
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        storage_path=payload.storage_path,
        checksum=payload.checksum,
        created_by_id=user_id,
    )
    db.add(version)
    doc.current_version = next_version
    await db.commit()
    await db.refresh(version)
    await db.refresh(doc)
    return _to_version_read(version)


async def create_ai_summary(
    db: AsyncSession, tenant_id: int, doc_id: int, user_id: int, payload: DocumentAISummaryCreate
) -> DocumentAISummaryRead:
    doc = await _get_document(db, tenant_id, doc_id)

    target_version_id = payload.version_id
    if target_version_id is None:
        target_version_id = doc.current_version
        if target_version_id is None:
            # try latest version
            res = await db.execute(
                select(DocumentVersion.id)
                .where(DocumentVersion.document_id == doc.id)
                .order_by(DocumentVersion.version_number.desc())
                .limit(1)
            )
            target_version_id = res.scalar_one_or_none()

    summary = DocumentAISummary(
        document_id=doc.id,
        version_id=target_version_id,
        language=payload.language or "en",
        model_name=None,
        summary_text="AI summary not implemented yet",
        created_by_id=user_id,
    )
    db.add(summary)
    await db.commit()
    await db.refresh(summary)
    return _to_summary_read(summary)
