import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.db.models.document import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


class DocumentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = Field(None, max_length=100)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = Field(None, max_length=100)


class DocumentOut(BaseModel):
    id: int
    tenant_id: int
    title: str
    description: Optional[str]
    status: Optional[str]
    type: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    model_config = {"from_attributes": True}


async def _get_document_or_404(db: AsyncSession, tenant_id: int, doc_id: int) -> Document:
    doc = await db.scalar(
        select(Document).where(Document.id == doc_id, Document.tenant_id == tenant_id, Document.deleted_at.is_(None))
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/", response_model=list[DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    try:
        stmt = (
            select(Document)
            .where(Document.tenant_id == ctx.tenant_id, Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )
        result = await db.execute(stmt)
        items = result.scalars().all()
        return [_serialize(doc) for doc in items]
    except Exception:
        try:
            logger.exception("Failed to list documents; returning empty list")
        except Exception:
            pass
        return []


@router.post("/", response_model=DocumentOut)
async def create_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    doc = Document(
        tenant_id=ctx.tenant_id,
        title=payload.title,
        description=payload.description,
        category=payload.type,
        status=payload.status or "active",
        deleted_at=None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return _serialize(doc)


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    doc = await _get_document_or_404(db, ctx.tenant_id, doc_id)
    return _serialize(doc)


@router.put("/{doc_id}", response_model=DocumentOut)
async def update_document(
    doc_id: int,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    doc = await _get_document_or_404(db, ctx.tenant_id, doc_id)
    if payload.title is not None:
        doc.title = payload.title
    if payload.description is not None:
        doc.description = payload.description
    if payload.status is not None:
        doc.status = payload.status
    if payload.type is not None:
        doc.category = payload.type
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return _serialize(doc)


@router.delete("/{doc_id}", response_model=dict)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    doc = await _get_document_or_404(db, ctx.tenant_id, doc_id)
    doc.deleted_at = datetime.utcnow()
    db.add(doc)
    await db.commit()
    return {"ok": True}


def _serialize(doc: Document) -> DocumentOut:
    # Map DB category to API "type"
    return DocumentOut(
        id=doc.id,
        tenant_id=doc.tenant_id,
        title=doc.title,
        description=doc.description,
        status=doc.status,
        type=doc.category,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        deleted_at=doc.deleted_at,
    )
