"""Add tenant plan/status for platform admin views

Revision ID: 0005_platform_admin_fields
Revises: 0004_onboarding_progress_analytics
Create Date: 2025-12-02 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_platform_admin_fields"
down_revision: Union[str, None] = "0004_onboarding_progress_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("plan", sa.String(), nullable=False, server_default="free"))
    op.add_column("tenants", sa.Column("status", sa.String(), nullable=False, server_default="active"))


def downgrade() -> None:
    op.drop_column("tenants", "status")
    op.drop_column("tenants", "plan")
