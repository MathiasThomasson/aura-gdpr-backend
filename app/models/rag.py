from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CreateKnowledgeDocumentRequest(BaseModel):
    title: Optional[str] = None
    content: str
    source: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[List[str]] = None

class KnowledgeDocumentResponse(BaseModel):
    id: int
    tenant_id: Optional[int]
    title: Optional[str]
    content: str
    source: Optional[str]
    language: Optional[str]
    tags: Optional[List[str]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
