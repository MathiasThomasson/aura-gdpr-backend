"""Add DSR status history and update status defaults

Revision ID: 0007_dsr_status_history
Revises: 0006_public_dsr_links
Create Date: 2025-12-02 21:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_dsr_status_history"
down_revision: Union[str, None] = "0006_public_dsr_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("data_subject_requests"):
        # Normalize legacy "open" status to "received" to align with new workflow
        op.execute(sa.text("UPDATE data_subject_requests SET status = 'received' WHERE status = 'open'"))
        # Ensure default status is "received" going forward
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("data_subject_requests") as batch_op:
                batch_op.alter_column("status", server_default="received")
        else:
            op.alter_column("data_subject_requests", "status", server_default="received", existing_type=sa.String(length=50))

    if not insp.has_table("dsr_status_history"):
        op.create_table(
            "dsr_status_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("dsr_id", sa.Integer(), sa.ForeignKey("data_subject_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("from_status", sa.String(length=50), nullable=True),
            sa.Column("to_status", sa.String(length=50), nullable=False),
            sa.Column("changed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("note", sa.Text(), nullable=True),
        )
        op.create_index("ix_dsr_status_history_id", "dsr_status_history", ["id"], unique=False)
        op.create_index("ix_dsr_status_history_dsr_id", "dsr_status_history", ["dsr_id"], unique=False)
        op.create_index("ix_dsr_status_history_changed_by_user_id", "dsr_status_history", ["changed_by_user_id"], unique=False)
        op.create_index("ix_dsr_status_history_changed_at", "dsr_status_history", ["changed_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("dsr_status_history"):
        op.drop_index("ix_dsr_status_history_changed_at", table_name="dsr_status_history")
        op.drop_index("ix_dsr_status_history_changed_by_user_id", table_name="dsr_status_history")
        op.drop_index("ix_dsr_status_history_dsr_id", table_name="dsr_status_history")
        op.drop_index("ix_dsr_status_history_id", table_name="dsr_status_history")
        op.drop_table("dsr_status_history")
