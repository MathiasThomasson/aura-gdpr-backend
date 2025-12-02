import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantBoundMixin


class Document(TenantBoundMixin, Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, server_default="active")
    current_version = Column(Integer, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now(), index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    tenant = relationship("Tenant")
    created_by = relationship("User")

    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    tags = relationship("DocumentTagLink", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number", name="uq_document_versions_doc_version"),)

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    storage_path = Column(String(512), nullable=True)
    checksum = Column(String(128), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)

    document = relationship("Document", back_populates="versions")
    created_by = relationship("User")
    summaries = relationship("DocumentAISummary", back_populates="version", cascade="all, delete-orphan")


class DocumentAISummary(Base):
    __tablename__ = "document_ai_summaries"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    language = Column(String(10), nullable=False, server_default="en")
    model_name = Column(String(100), nullable=True)
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document = relationship("Document")
    version = relationship("DocumentVersion", back_populates="summaries")
    created_by = relationship("User")


class DocumentTag(TenantBoundMixin, Base):
    __tablename__ = "document_tags"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_document_tags_tenant_name"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    tenant = relationship("Tenant")
    documents = relationship("DocumentTagLink", back_populates="tag", cascade="all, delete-orphan")


class DocumentTagLink(Base):
    __tablename__ = "document_tag_links"
    __table_args__ = (UniqueConstraint("document_id", "tag_id", name="uq_document_tag_links_document_tag"),)

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("document_tags.id", ondelete="CASCADE"), nullable=False, index=True)

    document = relationship("Document", back_populates="tags")
    tag = relationship("DocumentTag", back_populates="documents")
