from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentContext, current_context

router = APIRouter(prefix="/api/dpia", tags=["DPIA"])


class DPIAItem(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[datetime] = None


class DPIAListResponse(BaseModel):
    items: List[DPIAItem] = Field(default_factory=list)
    total: int = 0


@router.get("/", response_model=DPIAListResponse)
async def list_dpia(ctx: CurrentContext = Depends(current_context)):
    return DPIAListResponse()
