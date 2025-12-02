from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SimpleRecordBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = None


class SimpleRecordCreate(SimpleRecordBase):
    pass


class SimpleRecordUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class SimpleRecordOut(SimpleRecordBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
