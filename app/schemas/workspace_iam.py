from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, field_validator


WorkspaceRole = Literal["owner", "admin", "user", "viewer"]
WorkspaceStatus = Literal["active", "disabled"]


class WorkspaceUserBase(BaseModel):
    id: int  # user_tenant id
    user_id: int
    email: EmailStr
    full_name: Optional[str] = None
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkspaceUserListItem(WorkspaceUserBase):
    role: WorkspaceRole
    status: WorkspaceStatus


class WorkspaceUserInviteRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole


class WorkspaceUserUpdateRequest(BaseModel):
    role: Optional[WorkspaceRole] = None
    status: Optional[WorkspaceStatus] = None

    @field_validator("status")
    @classmethod
    def ensure_status(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ("active", "disabled"):
            raise ValueError("status must be either 'active' or 'disabled'")
        return v
