"""refresh token rotation fields and role safety

Revision ID: 20251126_refresh_rotation
Revises: 20251126_enforce_tenants
Create Date: 2025-11-26 00:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = "20251126_refresh_rotation"
down_revision: Union[str, None] = "20251126_enforce_tenants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Refresh tokens: add rotation-related fields
    op.add_column("refresh_tokens", sa.Column("family_id", sa.String(), nullable=True))
    op.add_column("refresh_tokens", sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("refresh_tokens", sa.Column("revoked_reason", sa.String(), nullable=True))
    op.add_column("refresh_tokens", sa.Column("replaced_by_token", sa.String(), nullable=True))
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"], unique=False)
    op.create_index("ix_refresh_tokens_replaced_by_token", "refresh_tokens", ["replaced_by_token"], unique=False)

    # Backfill family_id with a stable UUID per existing token
    conn = op.get_bind()
    tokens = conn.execute(sa.text("SELECT token FROM refresh_tokens")).fetchall()
    for (token,) in tokens:
        conn.execute(
            sa.text("UPDATE refresh_tokens SET family_id = :fid WHERE token = :t"),
            {"fid": str(uuid.uuid4()), "t": token},
        )

    # Make family_id non-null
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.alter_column("family_id", existing_type=sa.String(), nullable=False)

    # Optional: enforce allowed roles via check constraint (best-effort; SQLite may ignore)
    try:
        op.create_check_constraint(
            "ck_users_role_allowed",
            "users",
            "role in ('owner','admin','user')",
        )
    except Exception:
        # On SQLite, check constraints may be limited; ignore if unsupported
        pass


def downgrade() -> None:
    try:
        op.drop_constraint("ck_users_role_allowed", "users", type_="check")
    except Exception:
        pass
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.alter_column("family_id", existing_type=sa.String(), nullable=True)
    op.drop_index("ix_refresh_tokens_replaced_by_token", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "replaced_by_token")
    op.drop_column("refresh_tokens", "revoked_reason")
    op.drop_column("refresh_tokens", "last_used_at")
    op.drop_column("refresh_tokens", "family_id")
