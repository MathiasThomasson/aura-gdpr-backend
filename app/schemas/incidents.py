from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    severity: str = Field(..., pattern="^(low|medium|high)$")


class IncidentOut(BaseModel):
    id: int
    title: str
    severity: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
