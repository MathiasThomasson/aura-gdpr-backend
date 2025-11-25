from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    tenant_id: Optional[int]
    role: str

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

    model_config = {"from_attributes": True}
