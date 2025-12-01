from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BillingPlanRead(BaseModel):
    type: str
    name: str
    price_per_month: int
    currency: str
    is_trial: bool
    trial_days_left: Optional[int] = None
    features: List[str]

    model_config = {"from_attributes": True}


class BillingUsageRead(BaseModel):
    dsr_count_month: int
    documents_count: int
    policies_count: int
    ai_calls_month: int

    model_config = {"from_attributes": True}


class BillingInvoiceRead(BaseModel):
    id: int
    date: datetime
    amount: int
    currency: str
    description: Optional[str] = None
    status: str
    invoice_url: Optional[str] = None

    model_config = {"from_attributes": True}


class BillingInvoiceListResponse(BaseModel):
    items: List[BillingInvoiceRead]
    total: int

    model_config = {"from_attributes": True}
