from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.processing_activity import ProcessingActivity
from app.db.models.task import Task
from app.models.task_status import TaskStatus

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
    last_ai_query: Optional[datetime] = None
    recent_tasks: List[dict[str, Any]] = Field(default_factory=list)
    recent_documents: List[dict[str, Any]] = Field(default_factory=list)
    risk_overview: dict[str, Any] = Field(default_factory=lambda: {"high": 0, "medium": 0, "low": 0})
    generated_at: datetime


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    tenant_id = ctx.tenant_id

    document_count = await db.scalar(
        select(func.count()).select_from(Document).where(Document.tenant_id == tenant_id, Document.deleted_at.is_(None))
    ) or 0

    open_task_statuses = (TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value, TaskStatus.BLOCKED.value)
    open_task_count = await db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.tenant_id == tenant_id,
            Task.status.in_(open_task_statuses),
            Task.deleted_at.is_(None),
        )
    ) or 0

    active_project_count = await db.scalar(
        select(func.count()).select_from(ProcessingActivity).where(ProcessingActivity.tenant_id == tenant_id)
    ) or 0

    last_ai_query = await db.scalar(
        select(AuditLog.created_at)
        .where(AuditLog.tenant_id == tenant_id, AuditLog.entity_type == "ai_call")
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )

    return DashboardSummary(
        tenant_id=tenant_id,
        counts=DashboardCounts(
            tasks=open_task_count,
            documents=document_count,
            projects=active_project_count,
        ),
        last_ai_query=last_ai_query,
        generated_at=datetime.utcnow(),
    )
