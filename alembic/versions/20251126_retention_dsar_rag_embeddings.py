"""add dsar/retention fields and embeddings table

Revision ID: 20251126_retention_embeddings
Revises: 20251126_docs_tasks_status
Create Date: 2025-11-26 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251126_retention_embeddings"
down_revision: Union[str, None] = "20251126_docs_tasks_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Soft delete fields
    op.add_column("tasks", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"], unique=False)
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"], unique=False)

    # Embeddings table for RAG
    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("checksum", sa.String(length=64), nullable=False, index=True),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_knowledge_embeddings_tenant_id", "knowledge_embeddings", ["tenant_id"], unique=False)
    op.create_index("ix_knowledge_embeddings_checksum", "knowledge_embeddings", ["checksum"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_embeddings_checksum", table_name="knowledge_embeddings")
    op.drop_index("ix_knowledge_embeddings_tenant_id", table_name="knowledge_embeddings")
    op.drop_table("knowledge_embeddings")
    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_column("documents", "deleted_at")
    op.drop_index("ix_tasks_deleted_at", table_name="tasks")
    op.drop_column("tasks", "deleted_at")
