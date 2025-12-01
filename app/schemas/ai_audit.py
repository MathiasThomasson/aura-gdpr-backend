from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AuditRunRead(BaseModel):
    id: int
    created_at: datetime
    completed_at: Optional[datetime]
    overall_score: int
    areas: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]

    model_config = {"from_attributes": True}


class AuditRunListResponse(BaseModel):
    items: List[AuditRunRead]
    total: int

    model_config = {"from_attributes": True}
