from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.document import (
    DocumentAISummaryCreate,
    DocumentAISummaryRead,
    DocumentCreate,
    DocumentListResponse,
    DocumentRead,
    DocumentUpdate,
    DocumentVersionCreate,
    DocumentVersionRead,
)
from app.services.document_service import (
    add_version,
    create_ai_summary,
    create_document,
    delete_document,
    get_document,
    list_documents,
    list_versions,
    update_document,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("/", response_model=DocumentListResponse)
async def list_docs(
    q: str | None = None,
    category: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    return await list_documents(db, ctx.tenant_id, q, category, status, tag, skip, limit)


@router.post("/", response_model=DocumentRead)
async def create_doc(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    doc = await create_document(db, ctx.tenant_id, ctx.user.id, payload)
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc.id, "create", None)
    return doc


@router.get("/{doc_id}", response_model=DocumentRead)
async def get_doc(doc_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    return await get_document(db, ctx.tenant_id, doc_id)


@router.patch("/{doc_id}", response_model=DocumentRead)
async def update_doc(
    doc_id: int,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    doc = await update_document(db, ctx.tenant_id, doc_id, payload)
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc.id, "update", None)
    return doc


@router.delete("/{doc_id}")
async def delete_doc(doc_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    await delete_document(db, ctx.tenant_id, doc_id)
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc_id, "delete", None)
    return {"ok": True}


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionRead])
async def get_versions(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    return await list_versions(db, ctx.tenant_id, doc_id)


@router.post("/{doc_id}/versions", response_model=DocumentVersionRead)
async def create_version(
    doc_id: int,
    payload: DocumentVersionCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    version = await add_version(db, ctx.tenant_id, doc_id, ctx.user.id, payload)
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc_id, "version_create", {"version": version.version_number})
    return version


@router.post("/{doc_id}/summaries/ai", response_model=DocumentAISummaryRead)
async def create_ai_summary_endpoint(
    doc_id: int,
    payload: DocumentAISummaryCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    summary = await create_ai_summary(db, ctx.tenant_id, doc_id, ctx.user.id, payload)
    await log_event(db, ctx.tenant_id, ctx.user.id, "document", doc_id, "ai_summary_create", {"summary_id": summary.id})
    return summary
