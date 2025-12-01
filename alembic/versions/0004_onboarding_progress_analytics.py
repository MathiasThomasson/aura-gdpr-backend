"""Add onboarding, user progress, analytics, and incidents.

Revision ID: 0004_onboarding_progress_analytics
Revises: 0003_security_hardening
Create Date: 2025-12-02 00:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_onboarding_progress_analytics"
down_revision: Union[str, None] = "0003_security_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onboarding_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("onboarding_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_onboarding_states_id", "onboarding_states", ["id"], unique=False)
    op.create_index("ix_onboarding_states_user_id", "onboarding_states", ["user_id"], unique=False)
    op.create_index("ix_onboarding_states_tenant_id", "onboarding_states", ["tenant_id"], unique=False)

    op.create_table(
        "user_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_first_dsr", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_first_policy", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_first_dpia", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_first_ropa", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_first_tom", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("ran_ai_audit", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_user_progress_id", "user_progress", ["id"], unique=False)
    op.create_index("ix_user_progress_user_id", "user_progress", ["user_id"], unique=False)
    op.create_index("ix_user_progress_tenant_id", "user_progress", ["tenant_id"], unique=False)

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_analytics_events_id", "analytics_events", ["id"], unique=False)
    op.create_index("ix_analytics_events_tenant_id", "analytics_events", ["tenant_id"], unique=False)
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"], unique=False)
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_incidents_id", "incidents", ["id"], unique=False)
    op.create_index("ix_incidents_tenant_id", "incidents", ["tenant_id"], unique=False)
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_index("ix_incidents_tenant_id", table_name="incidents")
    op.drop_index("ix_incidents_id", table_name="incidents")
    op.drop_table("incidents")

    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_user_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_tenant_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_id", table_name="analytics_events")
    op.drop_table("analytics_events")

    op.drop_index("ix_user_progress_tenant_id", table_name="user_progress")
    op.drop_index("ix_user_progress_user_id", table_name="user_progress")
    op.drop_index("ix_user_progress_id", table_name="user_progress")
    op.drop_table("user_progress")

    op.drop_index("ix_onboarding_states_tenant_id", table_name="onboarding_states")
    op.drop_index("ix_onboarding_states_user_id", table_name="onboarding_states")
    op.drop_index("ix_onboarding_states_id", table_name="onboarding_states")
    op.drop_table("onboarding_states")
