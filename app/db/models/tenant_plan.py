import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base, TenantBoundMixin

try:
    JSONType = JSONB
except Exception:  # pragma: no cover - fallback for SQLite
    from sqlalchemy import JSON as JSONType  # type: ignore


class TenantPlan(TenantBoundMixin, Base):
    __tablename__ = "tenant_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    price_per_month = Column(Integer, nullable=False, server_default="0")
    currency = Column(String(10), nullable=False, server_default="USD")
    is_trial = Column(Boolean, nullable=False, server_default="0")
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    features = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
