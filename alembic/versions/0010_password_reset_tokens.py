"""Add password reset tokens table.

Revision ID: 0010_password_reset_tokens
Revises: 0009_audit_metadata_and_processing_activities
Create Date: 2025-12-03 02:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_password_reset_tokens"
down_revision: Union[str, None] = "0009_audit_metadata_and_processing_activities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("token", sa.String(), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"], unique=False)
        op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("password_reset_tokens"):
        op.drop_index("ix_password_reset_tokens_token", table_name="password_reset_tokens")
        op.drop_index("ix_password_reset_tokens_id", table_name="password_reset_tokens")
        op.drop_table("password_reset_tokens")
