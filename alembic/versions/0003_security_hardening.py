"""Add API keys and performance indexes.

Revision ID: 0003_security_hardening
Revises: 0002_product_modules
Create Date: 2025-12-02 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_security_hardening"
down_revision: Union[str, None] = "0002_product_modules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index_if_missing(insp, name: str, table: str, columns: list[str]) -> None:
    if not insp.has_table(table):
        return
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns, unique=False)


def upgrade() -> None:
    # API keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_id", "api_keys", ["id"], unique=False)
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"], unique=False)
    op.create_index("ix_api_keys_created_at", "api_keys", ["created_at"], unique=False)
    op.create_index("ix_api_keys_last_used_at", "api_keys", ["last_used_at"], unique=False)
    op.create_index("ix_api_keys_expires_at", "api_keys", ["expires_at"], unique=False)

    # Optional performance indexes on common filters
    insp = sa.inspect(op.get_bind())
    _create_index_if_missing(insp, "ix_tasks_created_at", "tasks", ["created_at"])
    _create_index_if_missing(insp, "ix_tasks_updated_at", "tasks", ["updated_at"])
    _create_index_if_missing(insp, "ix_tasks_tenant_id", "tasks", ["tenant_id"])
    _create_index_if_missing(insp, "ix_documents_created_at", "documents", ["created_at"])
    _create_index_if_missing(insp, "ix_documents_updated_at", "documents", ["updated_at"])
    _create_index_if_missing(insp, "ix_documents_tenant_id", "documents", ["tenant_id"])
    _create_index_if_missing(insp, "ix_document_versions_created_at", "document_versions", ["created_at"])
    _create_index_if_missing(insp, "ix_document_versions_document_id", "document_versions", ["document_id"])
    _create_index_if_missing(insp, "ix_document_ai_summaries_created_at", "document_ai_summaries", ["created_at"])
    _create_index_if_missing(insp, "ix_data_subject_requests_created_at", "data_subject_requests", ["created_at"])
    _create_index_if_missing(insp, "ix_data_subject_requests_updated_at", "data_subject_requests", ["updated_at"])
    _create_index_if_missing(insp, "ix_processing_activities_created_at", "processing_activities", ["created_at"])
    _create_index_if_missing(insp, "ix_processing_activities_updated_at", "processing_activities", ["updated_at"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    # drop indexes only if they exist
    for name, table in [
        ("ix_processing_activities_updated_at", "processing_activities"),
        ("ix_processing_activities_created_at", "processing_activities"),
        ("ix_data_subject_requests_updated_at", "data_subject_requests"),
        ("ix_data_subject_requests_created_at", "data_subject_requests"),
        ("ix_document_ai_summaries_created_at", "document_ai_summaries"),
        ("ix_document_versions_document_id", "document_versions"),
        ("ix_document_versions_created_at", "document_versions"),
        ("ix_documents_updated_at", "documents"),
        ("ix_documents_created_at", "documents"),
        ("ix_documents_tenant_id", "documents"),
        ("ix_tasks_updated_at", "tasks"),
        ("ix_tasks_created_at", "tasks"),
        ("ix_tasks_tenant_id", "tasks"),
    ]:
        if insp.has_table(table):
            existing = {idx["name"] for idx in insp.get_indexes(table)}
            if name in existing:
                op.drop_index(name, table_name=table)

    op.drop_index("ix_api_keys_expires_at", table_name="api_keys")
    op.drop_index("ix_api_keys_last_used_at", table_name="api_keys")
    op.drop_index("ix_api_keys_created_at", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys")
    op.drop_index("ix_api_keys_id", table_name="api_keys")
    op.drop_table("api_keys")
