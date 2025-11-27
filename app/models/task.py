from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.task_status import ALLOWED_TASK_STATUSES, TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    category: Optional[str] = None
    assigned_to_user_id: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_TASK_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_TASK_STATUSES)}")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    category: Optional[str] = None
    assigned_to_user_id: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_TASK_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_TASK_STATUSES)}")
        return v


class TaskOut(BaseModel):
    id: int
    tenant_id: int
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    status: str
    category: Optional[str]
    assigned_to_user_id: Optional[int]

    model_config = {"from_attributes": True}
