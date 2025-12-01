import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base, TenantBoundMixin


class ApiKey(TenantBoundMixin, Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
