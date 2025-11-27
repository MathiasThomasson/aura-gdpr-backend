from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.models.document import DocumentCreate, DocumentOut, DocumentUpdate
from app.services.document_service import (
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/", response_model=DocumentOut)
async def create_doc(payload: DocumentCreate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    doc = await create_document(
        db,
        tenant_id=ctx.tenant_id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        version=payload.version or 1,
    )
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc.id, "create", None)
    return doc


@router.get("/", response_model=list[DocumentOut])
async def list_docs(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    return await list_documents(db, ctx.tenant_id)


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_doc(doc_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    return await get_document(db, ctx.tenant_id, doc_id)


@router.put("/{doc_id}", response_model=DocumentOut)
async def update_doc(doc_id: int, payload: DocumentUpdate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    doc = await update_document(
        db,
        tenant_id=ctx.tenant_id,
        doc_id=doc_id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        version=payload.version,
    )
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc.id, "update", None)
    return doc


@router.delete("/{doc_id}")
async def delete_doc(doc_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    await delete_document(db, ctx.tenant_id, doc_id)
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc_id, "delete", None)
    return {"ok": True}
