import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantBoundMixin


class DataSubjectRequest(TenantBoundMixin, Base):
    __tablename__ = "data_subject_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column("type", String(50), nullable=False)
    subject_name = Column("data_subject", String(255), nullable=False)
    subject_email = Column("email", String(255), nullable=True)
    description = Column("notes", Text, nullable=True)
    priority = Column(String(20), nullable=False, server_default="medium")
    status = Column(String(50), nullable=False, server_default="received")
    source = Column(String(20), nullable=False, server_default="internal")
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    deadline = Column("due_at", DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    status_history = relationship("DSRStatusHistory", back_populates="dsr", cascade="all, delete-orphan")
