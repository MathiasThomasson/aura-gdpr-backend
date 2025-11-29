from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentContext, current_context

router = APIRouter(prefix="/api/projects", tags=["Projects"])


class ProjectSummary(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    updated_at: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    items: List[ProjectSummary] = Field(default_factory=list)
    total: int = 0


@router.get("/", response_model=ProjectListResponse)
async def list_projects(ctx: CurrentContext = Depends(current_context)):
    return ProjectListResponse()
