from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentContext, current_context

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


class DashboardCounts(BaseModel):
    tasks: int = 0
    documents: int = 0
    projects: int = 0
    dpias: int = 0
    risks: int = 0
    data_subject_requests: int = 0


class DashboardSummary(BaseModel):
    tenant_id: int
    counts: DashboardCounts = Field(default_factory=DashboardCounts)
    recent_tasks: List[dict[str, Any]] = Field(default_factory=list)
    recent_documents: List[dict[str, Any]] = Field(default_factory=list)
    risk_overview: dict[str, Any] = Field(default_factory=lambda: {"high": 0, "medium": 0, "low": 0})
    generated_at: datetime


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(ctx: CurrentContext = Depends(current_context)):
    return DashboardSummary(
        tenant_id=ctx.tenant_id,
        generated_at=datetime.utcnow(),
    )
