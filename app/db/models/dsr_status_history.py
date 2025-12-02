import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class DSRStatusHistory(Base):
    __tablename__ = "dsr_status_history"

    id = Column(Integer, primary_key=True, index=True)
    dsr_id = Column(Integer, ForeignKey("data_subject_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    note = Column(Text, nullable=True)

    dsr = relationship("DataSubjectRequest", back_populates="status_history")
