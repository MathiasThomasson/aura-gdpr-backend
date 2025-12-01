from pydantic import BaseModel, Field


class AnalyticsEventCreate(BaseModel):
    event_name: str = Field(..., max_length=100)


class AnalyticsEventOut(BaseModel):
    event_name: str
    tenant_id: int
    user_id: int

    model_config = {"from_attributes": True}
