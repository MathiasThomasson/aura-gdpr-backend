from pydantic import BaseModel
from typing import Optional


class ProcessingActivityCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProcessingActivityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProcessingActivityOut(BaseModel):
    id: int
    tenant_id: int
    name: str
    description: Optional[str]

    model_config = {"from_attributes": True}
