import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.db.base import Base, TenantBoundMixin


class Notification(TenantBoundMixin, Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, server_default="info")
    link = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    read = Column(Boolean, nullable=False, server_default="0")
