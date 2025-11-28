"""Documents module schema.

Revision ID: 0002_documents_module
Revises: 0001_core_schema
Create Date: 2025-11-28 00:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_documents_module"
down_revision: Union[str, None] = "0001_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # documents
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("current_version", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"], unique=False)

    # document_versions
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("storage_path", sa.String(length=512), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_doc_version"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"], unique=False)

    # document_ai_summaries
    op.create_table(
        "document_ai_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_document_ai_summaries_document_id", "document_ai_summaries", ["document_id"], unique=False)
    op.create_index("ix_document_ai_summaries_version_id", "document_ai_summaries", ["version_id"], unique=False)

    # document_tags
    op.create_table(
        "document_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_document_tags_tenant_name"),
    )
    op.create_index("ix_document_tags_tenant_id", "document_tags", ["tenant_id"], unique=False)

    # document_tag_links
    op.create_table(
        "document_tag_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("document_tags.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("document_id", "tag_id", name="uq_document_tag_links_document_tag"),
    )
    op.create_index("ix_document_tag_links_document_id", "document_tag_links", ["document_id"], unique=False)
    op.create_index("ix_document_tag_links_tag_id", "document_tag_links", ["tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_document_tag_links_tag_id", table_name="document_tag_links")
    op.drop_index("ix_document_tag_links_document_id", table_name="document_tag_links")
    op.drop_table("document_tag_links")

    op.drop_index("ix_document_tags_tenant_id", table_name="document_tags")
    op.drop_table("document_tags")

    op.drop_index("ix_document_ai_summaries_version_id", table_name="document_ai_summaries")
    op.drop_index("ix_document_ai_summaries_document_id", table_name="document_ai_summaries")
    op.drop_table("document_ai_summaries")

    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")
