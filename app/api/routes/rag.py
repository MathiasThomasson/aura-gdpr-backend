from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.models.rag import CreateKnowledgeDocumentRequest, KnowledgeDocumentResponse
from app.models.rag_search import RAGAnswer, RAGSearchRequest, RAGSearchResult
from app.services.rag_pipeline import normalize_text
from app.services.rag_service import create_document, list_documents, search

router = APIRouter(prefix="/api/rag", tags=["RAG"])


@router.post("/documents", response_model=KnowledgeDocumentResponse)
async def create_document_route(
    payload: CreateKnowledgeDocumentRequest,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    # enforce input length to avoid huge documents
    max_len = 200000
    content = payload.content
    if len(content) > max_len:
        raise HTTPException(status_code=400, detail=f"Content exceeds max length {max_len}")
    doc = await create_document(db, ctx.tenant_id, payload.title, content, payload.source, payload.language, payload.tags)
    return KnowledgeDocumentResponse.from_orm(doc)


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
async def get_documents(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    docs = await list_documents(db, ctx.tenant_id)
    return [KnowledgeDocumentResponse.from_orm(d) for d in docs]


@router.post("/search", response_model=RAGAnswer)
async def search_rag(payload: RAGSearchRequest, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    results = await search(db, ctx.tenant_id, normalize_text(payload.query), payload.top_k)
    items = []
    for score, chunk, emb in results:
        items.append(
            RAGSearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                score=score,
                chunk_index=chunk.chunk_index,
                model=emb.model or "hash-embed",
                section_title=chunk.section_title,
            )
        )
    answer_text = "Insufficient context"
    if items:
        # naive synthesis: concatenate top chunks
        context = "\n".join([i.content for i in items])
        answer_text = f"Relevant context:\n{context}"
    return RAGAnswer(answer=answer_text, citations=items)
