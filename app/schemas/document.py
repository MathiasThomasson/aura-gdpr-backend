from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentTagBase(BaseModel):
    name: str


class DocumentTagCreate(DocumentTagBase):
    pass


class DocumentTagRead(DocumentTagBase):
    id: int

    class Config:
        from_attributes = True


class DocumentVersionRead(BaseModel):
    id: int
    version_number: int
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentVersionCreate(BaseModel):
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    storage_path: Optional[str] = None


class DocumentAISummaryCreate(BaseModel):
    language: Optional[str] = "en"
    version_id: Optional[int] = None


class DocumentAISummaryRead(BaseModel):
    id: int
    document_id: int
    version_id: Optional[int] = None
    language: str
    model_name: Optional[str] = None
    summary_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    title: str
    category: Optional[str] = None
    status: Optional[str] = "active"
    tags: Optional[List[str]] = None  # tag names


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class DocumentRead(BaseModel):
    id: int
    title: str
    category: Optional[str] = None
    status: str
    current_version: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[DocumentTagRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentRead]
    total: int
