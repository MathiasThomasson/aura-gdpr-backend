import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserTenantRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


# Reuse the existing PostgreSQL enum created by Alembic; do not auto-create at runtime.
user_tenant_role_enum = postgresql.ENUM(
    "owner",
    "admin",
    "member",
    "viewer",
    name="user_tenant_role",
    create_type=False,
)


class UserTenant(Base):
    __tablename__ = "user_tenants"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role = Column(user_tenant_role_enum, nullable=False, server_default="member")
    is_active = Column(Boolean, nullable=False, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="tenants")
    tenant = relationship("Tenant", back_populates="users")
