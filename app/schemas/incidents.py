from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    severity: str = Field(default="low", pattern="^(low|medium|high)$")
    status: Optional[str] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    severity: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    status: Optional[str] = None


class IncidentOut(BaseModel):
    id: int
    tenant_id: int
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
