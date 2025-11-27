from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    content: str
    category: Optional[str] = Field(None, max_length=100)
    version: Optional[int] = 1


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    version: Optional[int] = None


class DocumentOut(BaseModel):
    id: int
    tenant_id: int
    title: str
    content: str
    category: Optional[str]
    version: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    model_config = {"from_attributes": True}
