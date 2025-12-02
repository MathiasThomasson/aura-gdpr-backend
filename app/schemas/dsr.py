from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, EmailStr, Field, computed_field, field_validator

ALLOWED_DSR_STATUSES = {"received", "identity_verification", "in_progress", "completed", "rejected"}
ALLOWED_DSR_PRIORITIES = {"low", "medium", "high"}
ALLOWED_DSR_SOURCES = {"internal", "public_form"}


class DSRBase(BaseModel):
    request_type: str = Field(validation_alias=AliasChoices("request_type", "type"))
    subject_name: str = Field(validation_alias=AliasChoices("subject_name", "data_subject"))
    subject_email: Optional[EmailStr] = Field(default=None, validation_alias=AliasChoices("subject_email", "email"))
    description: Optional[str] = Field(default=None, validation_alias=AliasChoices("description", "notes"))
    priority: str = "medium"
    received_at: Optional[datetime] = None
    deadline: Optional[datetime] = Field(default=None, validation_alias=AliasChoices("deadline", "due_at"))

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        normalized = v.lower()
        if normalized not in ALLOWED_DSR_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(ALLOWED_DSR_PRIORITIES)}")
        return normalized


class DSRCreate(DSRBase):
    status: str = "received"
    source: str = "internal"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ALLOWED_DSR_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_DSR_STATUSES)}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in ALLOWED_DSR_SOURCES:
            raise ValueError(f"source must be one of {sorted(ALLOWED_DSR_SOURCES)}")
        return v


class DSRUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = Field(default=None, validation_alias=AliasChoices("description", "notes"))
    priority: Optional[str] = None
    deadline: Optional[datetime] = Field(default=None, validation_alias=AliasChoices("deadline", "due_at"))

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_DSR_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_DSR_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.lower()
        if normalized not in ALLOWED_DSR_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(ALLOWED_DSR_PRIORITIES)}")
        return normalized


class DSROut(DSRBase):
    id: int
    tenant_id: int
    status: str
    source: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @computed_field
    @property
    def is_overdue(self) -> bool:
        if not self.deadline:
            return False
        deadline_date = self.deadline.date() if isinstance(self.deadline, datetime) else self.deadline
        today = datetime.utcnow().date()
        return deadline_date < today and self.status != "completed"

    model_config = {"from_attributes": True, "populate_by_name": True}


class PublicDSRCreate(BaseModel):
    request_type: str
    subject_name: str
    subject_email: EmailStr
    description: str
    priority: str

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        normalized = v.lower()
        if normalized not in ALLOWED_DSR_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(ALLOWED_DSR_PRIORITIES)}")
        return normalized


class DSRStatusChange(BaseModel):
    status: str
    note: Optional[str] = None
