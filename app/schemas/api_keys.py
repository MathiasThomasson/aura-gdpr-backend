from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    expires_at: Optional[datetime] = None


class ApiKeyOut(BaseModel):
    id: int
    name: str
    tenant_id: int
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyOut):
    key: str
