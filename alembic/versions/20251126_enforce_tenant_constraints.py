"""enforce tenant constraints and bind tokens to tenants

Revision ID: 20251126_enforce_tenants
Revises: 20251125_upgrade_json_to_jsonb
Create Date: 2025-11-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "20251126_enforce_tenants"
down_revision: Union[str, None] = "20251125_upgrade_json_to_jsonb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # Ensure tenants table exists (defensive for fresh/partial databases)
    if not inspector.has_table("tenants"):
        op.create_table(
            "tenants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
        op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)

    # Ensure password_reset_tokens table exists (legacy gap)
    if not inspector.has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("token", sa.String(), unique=True, nullable=False, index=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
    else:
        # Align default for existing tables to a proper boolean default
        try:
            with op.batch_alter_table("password_reset_tokens") as batch:
                batch.alter_column("used", existing_type=sa.Boolean(), server_default=sa.text("false"), nullable=False)
        except Exception:
            pass

    # Refresh tokens: add tenant_id and backfill from user
    op.add_column("refresh_tokens", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index("ix_refresh_tokens_tenant_id", "refresh_tokens", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_refresh_tokens_tenant_id", "refresh_tokens", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE"
    )
    op.execute(
        sa.text(
            "UPDATE refresh_tokens SET tenant_id = "
            "(SELECT tenant_id FROM users WHERE users.id = refresh_tokens.user_id) "
            "WHERE tenant_id IS NULL"
        )
    )
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)

    # Password reset tokens: add tenant_id and backfill from user
    op.add_column("password_reset_tokens", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_password_reset_tokens_tenant_id", "password_reset_tokens", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        "fk_password_reset_tokens_tenant_id", "password_reset_tokens", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE"
    )
    op.execute(
        sa.text(
            "UPDATE password_reset_tokens SET tenant_id = "
            "(SELECT tenant_id FROM users WHERE users.id = password_reset_tokens.user_id) "
            "WHERE tenant_id IS NULL"
        )
    )
    with op.batch_alter_table("password_reset_tokens") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)

    # Users: enforce tenant_id NOT NULL
    with op.batch_alter_table("users") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)

    # Knowledge documents/chunks: enforce tenant_id NOT NULL
    _ensure_no_nulls(bind, "knowledge_documents", "tenant_id")
    _ensure_no_nulls(bind, "knowledge_chunks", "tenant_id")
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("knowledge_chunks") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("knowledge_chunks") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table("users") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table("password_reset_tokens") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("fk_password_reset_tokens_tenant_id", "password_reset_tokens", type_="foreignkey")
    op.drop_index("ix_password_reset_tokens_tenant_id", table_name="password_reset_tokens")
    op.drop_column("password_reset_tokens", "tenant_id")

    with op.batch_alter_table("refresh_tokens") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("fk_refresh_tokens_tenant_id", "refresh_tokens", type_="foreignkey")
    op.drop_index("ix_refresh_tokens_tenant_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "tenant_id")


def _ensure_no_nulls(bind, table: str, column: str) -> None:
    res = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")).scalar()
    if res and res > 0:
        raise Exception(
            f"Cannot enforce NOT NULL on {table}.{column}: found {res} null rows. "
            "Backfill tenant_id before running this migration."
        )
