"""optional upgrade json to jsonb for postgres

Revision ID: 20251125_upgrade_json_to_jsonb
Revises: 20251125_create_rag_tables
Create Date: 2025-11-25 00:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251125_upgrade_json_to_jsonb'
down_revision: Union[str, None] = '20251125_create_rag_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        # No-op for non-Postgres DBs
        return

    # Convert tags and embedding to JSONB using ALTER TABLE ... USING ...
    try:
        op.execute("ALTER TABLE knowledge_documents ALTER COLUMN tags TYPE JSONB USING tags::jsonb")
        op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE JSONB USING embedding::jsonb")
    except Exception:
        # If columns or types already converted or not present, ignore
        pass


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    try:
        op.execute("ALTER TABLE knowledge_documents ALTER COLUMN tags TYPE JSON USING tags::json")
        op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE JSON USING embedding::json")
    except Exception:
        pass
