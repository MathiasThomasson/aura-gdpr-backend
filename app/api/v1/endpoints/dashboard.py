import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.processing_activity import ProcessingActivity
from app.db.models.task import Task
from app.models.task_status import TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


class DashboardSummaryResponse(BaseModel):
    total_documents: int = 0
    open_tasks: int = 0
    active_projects: int = 0
    last_ai_query_at: Optional[datetime] = None
    generated_at: datetime


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_summary(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    tenant_id = ctx.tenant_id

    total_documents = 0
    open_tasks = 0
    active_projects = 0
    last_ai_query = None

    try:
        total_documents = (
            await db.scalar(
                select(func.count()).select_from(Document).where(
                    Document.tenant_id == tenant_id, Document.deleted_at.is_(None)
                )
            )
        ) or 0

        open_task_statuses = (TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value, TaskStatus.BLOCKED.value)
        open_tasks = (
            await db.scalar(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.tenant_id == tenant_id,
                    Task.status.in_(open_task_statuses),
                    Task.deleted_at.is_(None),
                )
            )
        ) or 0

        active_projects = (
            await db.scalar(
                select(func.count()).select_from(ProcessingActivity).where(ProcessingActivity.tenant_id == tenant_id)
            )
        ) or 0

        last_ai_query = await db.scalar(
            select(AuditLog.created_at)
            .where(AuditLog.tenant_id == tenant_id, AuditLog.entity_type == "ai_call")
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
    except Exception:
        try:
            logger.exception("Dashboard summary query failed; returning fallbacks")
        except Exception:
            pass

    return DashboardSummaryResponse(
        total_documents=total_documents,
        open_tasks=open_tasks,
        active_projects=active_projects,
        last_ai_query_at=last_ai_query,
        generated_at=datetime.utcnow(),
    )
