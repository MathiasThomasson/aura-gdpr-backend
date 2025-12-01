import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base, TenantBoundMixin


class Incident(TenantBoundMixin, Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False, server_default="low")
    status = Column(String(50), nullable=False, server_default="open")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
