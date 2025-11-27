from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

from app.db.base import Base, TenantBoundMixin


class KnowledgeDocument(TenantBoundMixin, Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)
    language = Column(String(8), nullable=True)
    tags = Column(postgresql.JSONB().with_variant(JSON, 'sqlite'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
