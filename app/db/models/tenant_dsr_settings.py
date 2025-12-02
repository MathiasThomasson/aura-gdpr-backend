import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint

from app.db.base import Base, TenantBoundMixin


class TenantDSRSettings(TenantBoundMixin, Base):
    __tablename__ = "tenant_dsr_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_dsr_settings_tenant"),
        UniqueConstraint("public_dsr_key", name="uq_tenant_dsr_settings_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_dsr_key = Column(String(64), nullable=True)
    public_dsr_enabled = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), index=True)
