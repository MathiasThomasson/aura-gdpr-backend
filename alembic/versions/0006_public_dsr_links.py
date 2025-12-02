"""Add public DSR link settings and request fields

Revision ID: 0006_public_dsr_links
Revises: 0005_platform_admin_fields
Create Date: 2025-12-02 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_public_dsr_links"
down_revision: Union[str, None] = "0005_platform_admin_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table: str, column: str) -> bool:
    if not insp.has_table(table):
        return False
    return any(col["name"] == column for col in insp.get_columns(table))


def _drop_index_if_exists(insp, name: str, table: str) -> None:
    if not insp.has_table(table):
        return
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if name in existing:
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Dedicated table to store tenant public DSR configuration
    if not insp.has_table("tenant_dsr_settings"):
        op.create_table(
            "tenant_dsr_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("public_dsr_key", sa.String(length=64), nullable=True),
            sa.Column("public_dsr_enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.UniqueConstraint("tenant_id", name="uq_tenant_dsr_settings_tenant"),
            sa.UniqueConstraint("public_dsr_key", name="uq_tenant_dsr_settings_key"),
        )
        op.create_index("ix_tenant_dsr_settings_id", "tenant_dsr_settings", ["id"], unique=False)
        op.create_index("ix_tenant_dsr_settings_tenant_id", "tenant_dsr_settings", ["tenant_id"], unique=False)
        op.create_index("ix_tenant_dsr_settings_public_dsr_key", "tenant_dsr_settings", ["public_dsr_key"], unique=False)
        op.create_index("ix_tenant_dsr_settings_created_at", "tenant_dsr_settings", ["created_at"], unique=False)
        op.create_index("ix_tenant_dsr_settings_updated_at", "tenant_dsr_settings", ["updated_at"], unique=False)

    # Ensure DSR table exists (older migrations may have relied on metadata.create_all)
    if not insp.has_table("data_subject_requests"):
        op.create_table(
            "data_subject_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("data_subject", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
            sa.Column("source", sa.String(length=20), nullable=False, server_default="internal"),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_data_subject_requests_id", "data_subject_requests", ["id"], unique=False)
        op.create_index("ix_data_subject_requests_tenant_id", "data_subject_requests", ["tenant_id"], unique=False)
        op.create_index("ix_data_subject_requests_created_at", "data_subject_requests", ["created_at"], unique=False)
        op.create_index("ix_data_subject_requests_updated_at", "data_subject_requests", ["updated_at"], unique=False)
        op.create_index("ix_data_subject_requests_deleted_at", "data_subject_requests", ["deleted_at"], unique=False)
    else:
        # Add new fields if table already exists
        if not _has_column(insp, "data_subject_requests", "priority"):
            op.add_column("data_subject_requests", sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"))
        if not _has_column(insp, "data_subject_requests", "source"):
            op.add_column("data_subject_requests", sa.Column("source", sa.String(length=20), nullable=False, server_default="internal"))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("data_subject_requests"):
        if _has_column(insp, "data_subject_requests", "source"):
            op.drop_column("data_subject_requests", "source")
        if _has_column(insp, "data_subject_requests", "priority"):
            op.drop_column("data_subject_requests", "priority")

    if insp.has_table("tenant_dsr_settings"):
        _drop_index_if_exists(insp, "ix_tenant_dsr_settings_updated_at", "tenant_dsr_settings")
        _drop_index_if_exists(insp, "ix_tenant_dsr_settings_created_at", "tenant_dsr_settings")
        _drop_index_if_exists(insp, "ix_tenant_dsr_settings_public_dsr_key", "tenant_dsr_settings")
        _drop_index_if_exists(insp, "ix_tenant_dsr_settings_tenant_id", "tenant_dsr_settings")
        _drop_index_if_exists(insp, "ix_tenant_dsr_settings_id", "tenant_dsr_settings")
        op.drop_table("tenant_dsr_settings")
