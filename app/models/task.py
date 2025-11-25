from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    category: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    category: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


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
