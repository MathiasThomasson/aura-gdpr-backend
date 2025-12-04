from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.core.roles import ALLOWED_ROLES


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    tenant_id: Optional[int] = None  # optional for self-service sign-up
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password must match")
        return self


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetPerform(BaseModel):
    token: str
    new_password: str


class TokenMetadata(BaseModel):
    family_id: str
    issued_at: datetime
    expires_at: datetime
    revoked: bool
    revoked_reason: Optional[str] = None


class CurrentUserResponse(BaseModel):
    id: int
    email: EmailStr
    tenant_id: Optional[int] = None
    role: Optional[str] = None
    is_platform_owner: bool = False
