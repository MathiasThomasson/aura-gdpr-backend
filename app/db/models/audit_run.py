import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import settings
from app.db.base import Base, TenantBoundMixin

if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import JSON as JSONType  # type: ignore
else:  # pragma: no cover - prefer JSONB for Postgres
    try:
        JSONType = JSONB
    except Exception:  # pragma: no cover
        from sqlalchemy import JSON as JSONType  # type: ignore


class AuditRun(TenantBoundMixin, Base):
    __tablename__ = "audit_runs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    overall_score = Column(Integer, nullable=False)
    raw_result = Column(JSONType, nullable=False)
