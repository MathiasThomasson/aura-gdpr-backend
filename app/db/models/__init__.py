"""
Aggregator for SQLAlchemy models so Alembic can load metadata from a single place.
"""

from app.db.base import Base  # noqa: F401

# import models to register tables with Base.metadata
from app.db.models.user import User  # noqa: F401
from app.db.models.tenant import Tenant  # noqa: F401
from app.db.models.user_tenant import UserTenant, UserTenantRole  # noqa: F401
from app.db.models.refresh_token import RefreshToken  # noqa: F401
from app.db.models.audit_log import AuditLog  # noqa: F401
from app.db.models.settings import SystemSetting, TenantSetting  # noqa: F401
from app.db.models.document import (  # noqa: F401
    Document,
    DocumentVersion,
    DocumentAISummary,
    DocumentTag,
    DocumentTagLink,
)
