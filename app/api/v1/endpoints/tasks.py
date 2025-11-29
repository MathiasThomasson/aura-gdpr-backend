from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentContext, current_context

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


class TaskSummary(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    category: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


class TaskListResponse(BaseModel):
    items: List[TaskSummary] = Field(default_factory=list)
    total: int = 0


@router.get("/", response_model=TaskListResponse)
async def list_tasks(ctx: CurrentContext = Depends(current_context)):
    return TaskListResponse()
