from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentContext, current_context

router = APIRouter(prefix="/api/data-subject-requests", tags=["Data Subject Requests"])


class DataSubjectRequest(BaseModel):
    id: Optional[int] = None
    subject: Optional[str] = None
    request_type: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[datetime] = None


class DataSubjectRequestList(BaseModel):
    items: List[DataSubjectRequest] = Field(default_factory=list)
    total: int = 0


@router.get("/", response_model=DataSubjectRequestList)
async def list_requests(ctx: CurrentContext = Depends(current_context)):
    return DataSubjectRequestList()
