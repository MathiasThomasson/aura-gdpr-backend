"""Add GDPR CRUD modules, tasks table, and tenant test mode flag.

Revision ID: 0008_gdpr_crud_and_test_mode
Revises: 0007_dsr_status_history
Create Date: 2025-12-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_gdpr_crud_and_test_mode"
down_revision: Union[str, None] = "0007_dsr_status_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_simple_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index(f"ix_{name}_id", name, ["id"], unique=False)
    op.create_index(f"ix_{name}_tenant_id", name, ["tenant_id"], unique=False)
    op.create_index(f"ix_{name}_created_at", name, ["created_at"], unique=False)
    op.create_index(f"ix_{name}_updated_at", name, ["updated_at"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # Core CRUD modules
    for table in ("policies", "dpia_records", "ropa_records", "cookies", "toms", "projects"):
        if table not in existing_tables:
            _create_simple_table(table)

    # Tasks table
    if "tasks" not in existing_tables:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="open"),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_tasks_id", "tasks", ["id"], unique=False)
        op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"], unique=False)
        op.create_index("ix_tasks_created_at", "tasks", ["created_at"], unique=False)
        op.create_index("ix_tasks_updated_at", "tasks", ["updated_at"], unique=False)

    # Extend documents/incidents/tenants/DSR tables
    document_columns = [col["name"] for col in insp.get_columns("documents")]
    if "description" not in document_columns:
        op.add_column("documents", sa.Column("description", sa.Text(), nullable=True))

    incident_columns = [col["name"] for col in insp.get_columns("incidents")]
    if "description" not in incident_columns:
        op.add_column("incidents", sa.Column("description", sa.Text(), nullable=True))
    if "updated_at" not in incident_columns:
        op.add_column(
            "incidents",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    tenant_columns = [col["name"] for col in insp.get_columns("tenants")]
    if "is_test_tenant" not in tenant_columns:
        op.add_column("tenants", sa.Column("is_test_tenant", sa.Boolean(), nullable=False, server_default="1"))

    try:
        op.alter_column("data_subject_requests", "status", server_default="received")
    except Exception:
        # SQLite may not support altering server defaults; values are enforced in application code.
        pass


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # Drop newly added CRUD tables
    for table in ("projects", "toms", "cookies", "ropa_records", "dpia_records", "policies"):
        if table in existing_tables:
            op.drop_index(f"ix_{table}_updated_at", table_name=table)
            op.drop_index(f"ix_{table}_created_at", table_name=table)
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
            op.drop_index(f"ix_{table}_id", table_name=table)
            op.drop_table(table)

    # Drop tasks table if created by this migration
    if "tasks" in existing_tables:
        op.drop_index("ix_tasks_updated_at", table_name="tasks")
        op.drop_index("ix_tasks_created_at", table_name="tasks")
        op.drop_index("ix_tasks_tenant_id", table_name="tasks")
        op.drop_index("ix_tasks_id", table_name="tasks")
        op.drop_table("tasks")

    # Remove added columns
    document_columns = [col["name"] for col in insp.get_columns("documents")]
    if "description" in document_columns:
        op.drop_column("documents", "description")

    incident_columns = [col["name"] for col in insp.get_columns("incidents")]
    if "updated_at" in incident_columns:
        op.drop_column("incidents", "updated_at")
    if "description" in incident_columns:
        op.drop_column("incidents", "description")

    tenant_columns = [col["name"] for col in insp.get_columns("tenants")]
    if "is_test_tenant" in tenant_columns:
        op.drop_column("tenants", "is_test_tenant")
