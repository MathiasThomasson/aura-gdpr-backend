import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base, TenantBoundMixin


class ROPA(TenantBoundMixin, Base):
    __tablename__ = "ropa_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), index=True)
