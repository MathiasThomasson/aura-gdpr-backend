from typing import List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document


async def create_document(
    db: AsyncSession,
    tenant_id: int,
    title: str,
    content: str,
    category: Optional[str],
    version: int,
) -> Document:
    doc = Document(
        tenant_id=tenant_id,
        title=title,
        content=content,
        category=category,
        version=version or 1,
        deleted_at=None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_documents(db: AsyncSession, tenant_id: int) -> List[Document]:
    res = await db.execute(select(Document).where(Document.tenant_id == tenant_id, Document.deleted_at.is_(None)).order_by(Document.id.desc()))
    return res.scalars().all()


async def get_document(db: AsyncSession, tenant_id: int, doc_id: int) -> Optional[Document]:
    res = await db.execute(select(Document).where(Document.id == doc_id, Document.tenant_id == tenant_id, Document.deleted_at.is_(None)))
    return res.scalars().first()


async def save_document(db: AsyncSession, doc: Document) -> Document:
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(db: AsyncSession, doc: Document) -> None:
    doc.deleted_at = datetime.utcnow()
    db.add(doc)
    await db.commit()
