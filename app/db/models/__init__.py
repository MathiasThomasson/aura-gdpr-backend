"""
Aggregator for SQLAlchemy models so Alembic can load metadata from a single place.
"""

from app.db.base import Base  # noqa: F401

# import models to register tables with Base.metadata
from app.db.models.user import User  # noqa: F401
from app.db.models.tenant import Tenant  # noqa: F401
from app.db.models.user_tenant import UserTenant  # noqa: F401
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
from app.db.models.policy import Policy  # noqa: F401
from app.db.models.dpia import DPIA  # noqa: F401
from app.db.models.ropa import ROPA  # noqa: F401
from app.db.models.cookie import Cookie  # noqa: F401
from app.db.models.tom import TOM  # noqa: F401
from app.db.models.project import Project  # noqa: F401
from app.db.models.task import Task  # noqa: F401
from app.db.models.dsr import DataSubjectRequest  # noqa: F401
from app.db.models.dsr_status_history import DSRStatusHistory  # noqa: F401
from app.db.models.notification import Notification  # noqa: F401
from app.db.models.audit_run import AuditRun  # noqa: F401
from app.db.models.tenant_plan import TenantPlan  # noqa: F401
from app.db.models.billing_invoice import BillingInvoice  # noqa: F401
from app.db.models.api_key import ApiKey  # noqa: F401
from app.db.models.onboarding import OnboardingState  # noqa: F401
from app.db.models.user_progress import UserProgress  # noqa: F401
from app.db.models.analytics_event import AnalyticsEvent  # noqa: F401
from app.db.models.incident import Incident  # noqa: F401
from app.db.models.tenant_dsr_settings import TenantDSRSettings  # noqa: F401
from app.db.models.processing_activity import ProcessingActivity  # noqa: F401
from app.db.models.knowledge_document import KnowledgeDocument  # noqa: F401
from app.db.models.knowledge_chunk import KnowledgeChunk  # noqa: F401
from app.db.models.knowledge_embedding import KnowledgeEmbedding  # noqa: F401
from app.db.models.password_reset_token import PasswordResetToken  # noqa: F401
