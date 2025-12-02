"""Add audit log metadata and processing activities table.

Revision ID: 0009_audit_metadata_and_processing_activities
Revises: 0008_gdpr_crud_and_test_mode
Create Date: 2025-12-03 01:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_audit_metadata_and_processing_activities"
down_revision: Union[str, None] = "0008_gdpr_crud_and_test_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("audit_logs"):
        if not insp.has_column("audit_logs", "metadata"):
            op.add_column("audit_logs", sa.Column("metadata", sa.JSON(), nullable=True))
        if not insp.has_column("audit_logs", "meta"):
            op.add_column("audit_logs", sa.Column("meta", sa.JSON(), nullable=True))

    if not insp.has_table("processing_activities"):
        op.create_table(
            "processing_activities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index("ix_processing_activities_id", "processing_activities", ["id"], unique=False)
        op.create_index("ix_processing_activities_tenant_id", "processing_activities", ["tenant_id"], unique=False)
        op.create_index("ix_processing_activities_created_at", "processing_activities", ["created_at"], unique=False)
        op.create_index("ix_processing_activities_updated_at", "processing_activities", ["updated_at"], unique=False)

    if not insp.has_table("knowledge_documents"):
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("language", sa.String(length=8), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        )
        op.create_index("ix_knowledge_documents_id", "knowledge_documents", ["id"], unique=False)
        op.create_index("ix_knowledge_documents_tenant_id", "knowledge_documents", ["tenant_id"], unique=False)
        op.create_index("ix_knowledge_documents_created_at", "knowledge_documents", ["created_at"], unique=False)

    if not insp.has_table("knowledge_chunks"):
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=True),
            sa.Column("section_title", sa.String(length=255), nullable=True),
            sa.Column("checksum", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_knowledge_chunks_id", "knowledge_chunks", ["id"], unique=False)
        op.create_index("ix_knowledge_chunks_tenant_id", "knowledge_chunks", ["tenant_id"], unique=False)
        op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"], unique=False)
        op.create_index("ix_knowledge_chunks_checksum", "knowledge_chunks", ["checksum"], unique=False)

    if not insp.has_table("knowledge_embeddings"):
        op.create_table(
            "knowledge_embeddings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("checksum", sa.String(length=64), nullable=False),
            sa.Column("vector", sa.JSON(), nullable=False),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_knowledge_embeddings_id", "knowledge_embeddings", ["id"], unique=False)
        op.create_index("ix_knowledge_embeddings_tenant_id", "knowledge_embeddings", ["tenant_id"], unique=False)
        op.create_index("ix_knowledge_embeddings_chunk_id", "knowledge_embeddings", ["chunk_id"], unique=False)
        op.create_index("ix_knowledge_embeddings_document_id", "knowledge_embeddings", ["document_id"], unique=False)
        op.create_index("ix_knowledge_embeddings_checksum", "knowledge_embeddings", ["checksum"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("processing_activities"):
        op.drop_index("ix_processing_activities_updated_at", table_name="processing_activities")
        op.drop_index("ix_processing_activities_created_at", table_name="processing_activities")
        op.drop_index("ix_processing_activities_tenant_id", table_name="processing_activities")
        op.drop_index("ix_processing_activities_id", table_name="processing_activities")
        op.drop_table("processing_activities")

    if insp.has_table("knowledge_embeddings"):
        op.drop_index("ix_knowledge_embeddings_checksum", table_name="knowledge_embeddings")
        op.drop_index("ix_knowledge_embeddings_document_id", table_name="knowledge_embeddings")
        op.drop_index("ix_knowledge_embeddings_chunk_id", table_name="knowledge_embeddings")
        op.drop_index("ix_knowledge_embeddings_tenant_id", table_name="knowledge_embeddings")
        op.drop_index("ix_knowledge_embeddings_id", table_name="knowledge_embeddings")
        op.drop_table("knowledge_embeddings")

    if insp.has_table("knowledge_chunks"):
        op.drop_index("ix_knowledge_chunks_checksum", table_name="knowledge_chunks")
        op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
        op.drop_index("ix_knowledge_chunks_tenant_id", table_name="knowledge_chunks")
        op.drop_index("ix_knowledge_chunks_id", table_name="knowledge_chunks")
        op.drop_table("knowledge_chunks")

    if insp.has_table("knowledge_documents"):
        op.drop_index("ix_knowledge_documents_created_at", table_name="knowledge_documents")
        op.drop_index("ix_knowledge_documents_tenant_id", table_name="knowledge_documents")
        op.drop_index("ix_knowledge_documents_id", table_name="knowledge_documents")
        op.drop_table("knowledge_documents")

    if insp.has_table("audit_logs"):
        if insp.has_column("audit_logs", "meta"):
            op.drop_column("audit_logs", "meta")
        if insp.has_column("audit_logs", "metadata"):
            op.drop_column("audit_logs", "metadata")
