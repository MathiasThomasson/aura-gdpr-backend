from typing import List, Optional
import hashlib

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge_chunk import KnowledgeChunk
from app.db.models.knowledge_document import KnowledgeDocument
from app.db.models.knowledge_embedding import KnowledgeEmbedding
from app.services.rag_pipeline import normalize_text, chunk_text, embedding_for_text, cosine_similarity


async def create_document(
    db: AsyncSession,
    tenant_id: int,
    title: Optional[str],
    content: str,
    source: Optional[str],
    language: Optional[str],
    tags: Optional[List[str]] = None,
):
    doc = KnowledgeDocument(
        tenant_id=tenant_id,
        title=title,
        content=content,
        source=source,
        language=language,
        tags=tags,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    # ingest: chunk + embed
    await ingest_document(db, doc, tenant_id)
    return doc


async def ingest_document(db: AsyncSession, doc: KnowledgeDocument, tenant_id: int):
    normalized = normalize_text(doc.content or "")
    chunks = chunk_text(normalized, overlap_ratio=0.15)
    created_chunks = []
    embeddings = []
    for text, idx, section_title in chunks:
        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # deduplicate by checksum for this document
        existing = await db.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.document_id == doc.id,
                KnowledgeChunk.tenant_id == tenant_id,
                KnowledgeChunk.checksum == checksum,
            )
        )
        if existing.scalars().first():
            continue
        kc = KnowledgeChunk(
            tenant_id=tenant_id,
            document_id=doc.id,
            chunk_index=idx,
            content=text,
            embedding=None,
            section_title=section_title,
            checksum=checksum,
        )
        db.add(kc)
        created_chunks.append(kc)
    await db.commit()
    for kc in created_chunks:
        await db.refresh(kc)
        vec = embedding_for_text(kc.content)
        emb = KnowledgeEmbedding(
            tenant_id=tenant_id,
            chunk_id=kc.id,
            document_id=doc.id,
            checksum=kc.checksum or hashlib.sha256(kc.content.encode("utf-8")).hexdigest(),
            vector=vec,
            model="hash-embed",
        )
        db.add(emb)
        embeddings.append(emb)
    await db.commit()
    for emb in embeddings:
        await db.refresh(emb)
    return created_chunks


async def list_documents(db: AsyncSession, tenant_id: int):
    q = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id))
    return q.scalars().all()


async def list_chunks(db: AsyncSession, tenant_id: int, document_id: int):
    q = await db.execute(
        select(KnowledgeChunk).where(
            KnowledgeChunk.document_id == document_id,
            KnowledgeChunk.tenant_id == tenant_id,
        )
    )
    return q.scalars().all()


async def search(db: AsyncSession, tenant_id: int, query: str, top_k: int = 5):
    # simple similarity search over stored embeddings
    query_vec = embedding_for_text(query)
    res = await db.execute(
        select(KnowledgeEmbedding, KnowledgeChunk).join(KnowledgeChunk, KnowledgeChunk.id == KnowledgeEmbedding.chunk_id).where(
            KnowledgeEmbedding.tenant_id == tenant_id
        )
    )
    results = []
    for emb, chunk in res:
        score = cosine_similarity(query_vec, emb.vector)
        results.append((score, chunk, emb))
    results.sort(key=lambda x: x[0], reverse=True)
    # apply soft threshold
    threshold = 0.2
    filtered = [r for r in results if r[0] >= threshold]
    return filtered[:top_k]


async def delete_rag_for_tenant(db: AsyncSession, tenant_id: int):
    await db.execute(delete(KnowledgeEmbedding).where(KnowledgeEmbedding.tenant_id == tenant_id))
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.tenant_id == tenant_id))
    await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id))
    await db.commit()
