from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_repository import (
    create_document as repo_create,
    delete_document as repo_delete,
    get_document as repo_get,
    list_documents as repo_list,
    save_document as repo_save,
)


async def create_document(
    db: AsyncSession,
    tenant_id: int,
    title: str,
    content: str,
    category: Optional[str],
    version: int,
):
    return await repo_create(db, tenant_id, title, content, category, version or 1)


async def list_documents(db: AsyncSession, tenant_id: int):
    return await repo_list(db, tenant_id)


async def get_document(db: AsyncSession, tenant_id: int, doc_id: int):
    doc = await repo_get(db, tenant_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


async def update_document(
    db: AsyncSession,
    tenant_id: int,
    doc_id: int,
    title: Optional[str],
    content: Optional[str],
    category: Optional[str],
    version: Optional[int],
):
    doc = await get_document(db, tenant_id, doc_id)
    for field, val in {
        "title": title,
        "content": content,
        "category": category,
        "version": version,
    }.items():
        if val is not None:
            setattr(doc, field, val)
    return await repo_save(db, doc)


async def delete_document(db: AsyncSession, tenant_id: int, doc_id: int):
    doc = await get_document(db, tenant_id, doc_id)
    await repo_delete(db, doc)
    return doc
