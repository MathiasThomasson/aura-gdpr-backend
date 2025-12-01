import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base, TenantBoundMixin


class AnalyticsEvent(TenantBoundMixin, Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    event_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
