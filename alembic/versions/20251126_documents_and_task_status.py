"""add documents table and task status constraint

Revision ID: 20251126_documents_and_task_status
Revises: 20251126_refresh_rotation_and_roles
Create Date: 2025-11-26 00:25:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251126_documents_and_task_status"
down_revision: Union[str, None] = "20251126_refresh_rotation_and_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"], unique=False)
    op.create_index("ix_documents_id", "documents", ["id"], unique=False)

    # Tasks: ensure status default and allowed values
    op.execute("UPDATE tasks SET status = 'open' WHERE status IS NULL")
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("status", existing_type=sa.String(), nullable=False, server_default="open")
        try:
            batch.create_check_constraint(
                "ck_tasks_status_allowed",
                "status in ('open','in_progress','completed','blocked','archived')",
            )
        except Exception:
            # SQLite may not enforce; best-effort
            pass


def downgrade() -> None:
    try:
        with op.batch_alter_table("tasks") as batch:
            batch.drop_constraint("ck_tasks_status_allowed", type_="check")
            batch.alter_column("status", existing_type=sa.String(), nullable=True, server_default=None)
    except Exception:
        pass
    op.drop_index("ix_documents_id", table_name="documents")
    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")
