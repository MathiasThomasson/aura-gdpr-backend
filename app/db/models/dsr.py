import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base, TenantBoundMixin


class DataSubjectRequest(TenantBoundMixin, Base):
    __tablename__ = "data_subject_requests"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)
    data_subject = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, server_default="open")
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    due_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
