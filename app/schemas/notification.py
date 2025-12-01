from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    type: str
    title: str
    description: Optional[str] = None
    severity: str
    link: Optional[str] = None
    created_at: datetime
    read: bool

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: List[NotificationRead]
    total: int

    model_config = {"from_attributes": True}
