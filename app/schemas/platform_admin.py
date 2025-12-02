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
