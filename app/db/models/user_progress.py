import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, Boolean

from app.db.base import Base, TenantBoundMixin


class UserProgress(TenantBoundMixin, Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    created_first_dsr = Column(Boolean, nullable=False, server_default="0")
    created_first_policy = Column(Boolean, nullable=False, server_default="0")
    created_first_dpia = Column(Boolean, nullable=False, server_default="0")
    created_first_ropa = Column(Boolean, nullable=False, server_default="0")
    created_first_tom = Column(Boolean, nullable=False, server_default="0")
    ran_ai_audit = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
