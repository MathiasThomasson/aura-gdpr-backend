import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base, TenantBoundMixin


class BillingInvoice(TenantBoundMixin, Base):
    __tablename__ = "billing_invoices"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, server_default="USD")
    description = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, server_default="open")
    invoice_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
