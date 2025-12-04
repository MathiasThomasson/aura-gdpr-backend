from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlatformOverviewResponse(BaseModel):
    total_tenants: int
    total_users: int
    total_dsrs: int
    total_dpias: int


class PlatformTenantListItem(BaseModel):
    id: int
    name: str
    plan: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformTenantDetailResponse(BaseModel):
    id: int
    name: str
    plan: str
    status: str
    created_at: datetime
    total_users: int
    total_dsrs: int
    total_dpias: int
    last_activity_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PlatformUserItem(BaseModel):
    id: int
    email: str
    role: str
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    last_login_at: Optional[datetime] = None
    status: str


class PlatformPlan(BaseModel):
    id: str
    name: str
    monthly_price_eur: float
    yearly_price_eur: float
    paypal_product_id: Optional[str] = None
    paypal_plan_id_monthly: Optional[str] = None
    paypal_plan_id_yearly: Optional[str] = None
    included_ai_tokens: int
    max_users: int
    features: list[str] = []


class PlatformBillingStatus(BaseModel):
    tenant_id: int
    plan: str
    billing_cycle: str
    next_payment_date: Optional[datetime] = None
    paypal_subscription_id: Optional[str] = None
    status: str
    payment_history: list[dict] = []


class PayPalConfig(BaseModel):
    mode: str = "sandbox"
    client_id_masked: str = ""
    webhook_id: Optional[str] = None


class PayPalWebhookEvent(BaseModel):
    event_id: str
    event_type: str
    status: str
    received_at: datetime
    tenant_id: Optional[int] = None
    message: Optional[str] = None


class AIUsageItem(BaseModel):
    tenant_id: int
    tenant_name: str
    plan: str
    ai_tokens_30d: int
    ai_calls_30d: int
    overage_tokens: int
    status: str
    limits: Optional[dict] = None


class AIUsageSummary(BaseModel):
    tokens_24h: int
    tokens_7d: int
    tokens_30d: int
    cost_eur_estimate: float
    items: list[AIUsageItem] = []


class LogItem(BaseModel):
    timestamp: datetime
    level: str
    service: str
    tenant_id: Optional[int] = None
    message: str
    details: Optional[str] = None


class JobStatus(BaseModel):
    name: str
    last_run: Optional[datetime]
    status: str
    message: Optional[str] = None


class WebhookItem(BaseModel):
    id: str
    name: str
    target_url: str
    events: list[str]
    status: str
    last_delivery_status: Optional[str] = None


class ApiKeyItem(BaseModel):
    id: str
    name: str
    key_id: str
    created_at: datetime
    last_used: Optional[datetime] = None
    scopes: list[str]
    status: str


class FeatureFlagItem(BaseModel):
    name: str
    description: Optional[str] = None
    status: bool
    scope: str = "global"


class GlobalConfig(BaseModel):
    default_ai_model: str = "gpt-4o"
    max_upload_mb: int = 20
    global_rate_limit_rpm: int = 1000
    dsr_default_deadline_days: int = 30
    monthly_audit_day: int = 1
