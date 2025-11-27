from sqlalchemy import Column, DateTime, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

from app.db.base import Base, TenantBoundMixin


class KnowledgeChunk(TenantBoundMixin, Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(postgresql.JSONB().with_variant(JSON, 'sqlite'), nullable=True)
    section_title = Column(String(255), nullable=True)
    checksum = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
