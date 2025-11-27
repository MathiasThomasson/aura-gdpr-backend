from sqlalchemy import Column, Integer, ForeignKey, Float, JSON, DateTime
from sqlalchemy.sql import func

from app.db.base import Base, TenantBoundMixin


class KnowledgeEmbedding(TenantBoundMixin, Base):
    __tablename__ = "knowledge_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    checksum = Column(String(64), nullable=False, index=True)
    vector = Column(JSON, nullable=False)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
