"""add chunk metadata fields

Revision ID: 20251126_rag_chunk_metadata
Revises: 20251126_retention_dsar_rag_embeddings
Create Date: 2025-11-26 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251126_rag_chunk_metadata"
down_revision: Union[str, None] = "20251126_retention_dsar_rag_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_chunks", sa.Column("section_title", sa.String(length=255), nullable=True))
    op.add_column("knowledge_chunks", sa.Column("checksum", sa.String(length=64), nullable=True))
    op.create_index("ix_knowledge_chunks_checksum", "knowledge_chunks", ["checksum"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_checksum", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "checksum")
    op.drop_column("knowledge_chunks", "section_title")
