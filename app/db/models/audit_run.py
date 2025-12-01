import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base, TenantBoundMixin

try:
    JSONType = JSONB
except Exception:  # pragma: no cover - fallback for non-Postgres
    from sqlalchemy import JSON as JSONType  # type: ignore


class AuditRun(TenantBoundMixin, Base):
    __tablename__ = "audit_runs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    overall_score = Column(Integer, nullable=False)
    raw_result = Column(JSONType, nullable=False)
