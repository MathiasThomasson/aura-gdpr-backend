import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, Boolean

from app.db.base import Base, TenantBoundMixin


class OnboardingState(TenantBoundMixin, Base):
    __tablename__ = "onboarding_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    onboarding_completed = Column(Boolean, nullable=False, server_default="0")
    onboarding_step = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
