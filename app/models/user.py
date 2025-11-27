from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.core.roles import ALLOWED_ROLES


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[int] = None  # required for auth/register into existing tenant
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
        return v


class UserOut(BaseModel):
    id: int
    email: EmailStr
    tenant_id: Optional[int]
    role: str

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
        return v
