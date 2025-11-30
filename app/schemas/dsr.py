from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

ALLOWED_DSR_STATUSES = {"open", "in_progress", "completed", "rejected"}


class DSRBase(BaseModel):
    type: str
    data_subject: str
    email: Optional[EmailStr] = None
    received_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    notes: Optional[str] = None


class DSRCreate(DSRBase):
    status: str = "open"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ALLOWED_DSR_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_DSR_STATUSES)}")
        return v


class DSRUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    due_at: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_DSR_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_DSR_STATUSES)}")
        return v


class DSROut(DSRBase):
    id: int
    tenant_id: int
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
