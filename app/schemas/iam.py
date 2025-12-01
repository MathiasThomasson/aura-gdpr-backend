from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.core.roles import ALLOWED_ROLES


ALLOWED_IAM_STATUSES = {"active", "disabled", "pending_invite"}


class IamUserRead(BaseModel):
    id: int
    name: Optional[str] = None
    email: EmailStr
    role: str
    status: str
    last_login: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IamUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None
    action: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ALLOWED_IAM_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_IAM_STATUSES)}")
        return v


class InviteUserRequest(BaseModel):
    name: str
    email: EmailStr
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
        return v
