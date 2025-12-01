"""Add notifications, audit runs, billing and IAM columns.

Revision ID: 0002_product_modules
Revises: 0001_core_schema
Create Date: 2025-12-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_product_modules"
down_revision: Union[str, None] = "0001_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User IAM fields
    op.add_column("users", sa.Column("status", sa.String(), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
        sa.Column("link", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)

    # AI audit runs
    op.create_table(
        "audit_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("raw_result", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_runs_id", "audit_runs", ["id"], unique=False)
    op.create_index("ix_audit_runs_tenant_id", "audit_runs", ["tenant_id"], unique=False)
    op.create_index("ix_audit_runs_created_at", "audit_runs", ["created_at"], unique=False)

    # Tenant plans
    op.create_table(
        "tenant_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price_per_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("is_trial", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tenant_plans_id", "tenant_plans", ["id"], unique=False)
    op.create_index("ix_tenant_plans_tenant_id", "tenant_plans", ["tenant_id"], unique=False)

    # Billing invoices
    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("invoice_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_billing_invoices_id", "billing_invoices", ["id"], unique=False)
    op.create_index("ix_billing_invoices_tenant_id", "billing_invoices", ["tenant_id"], unique=False)
    op.create_index("ix_billing_invoices_status", "billing_invoices", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_invoices_status", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_tenant_id", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_id", table_name="billing_invoices")
    op.drop_table("billing_invoices")

    op.drop_index("ix_tenant_plans_tenant_id", table_name="tenant_plans")
    op.drop_index("ix_tenant_plans_id", table_name="tenant_plans")
    op.drop_table("tenant_plans")

    op.drop_index("ix_audit_runs_created_at", table_name="audit_runs")
    op.drop_index("ix_audit_runs_tenant_id", table_name="audit_runs")
    op.drop_index("ix_audit_runs_id", table_name="audit_runs")
    op.drop_table("audit_runs")

    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_tenant_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_column("users", "last_login_at")
    op.drop_column("users", "invited_at")
    op.drop_column("users", "status")
