from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.processing_activity import ProcessingActivity
from app.db.models.task import Task
from app.models.task_status import TaskStatus

try:
    from asyncpg.exceptions import UndefinedTableError as AsyncpgUndefinedTableError
except Exception:  # pragma: no cover - optional dependency guard
    class AsyncpgUndefinedTableError(Exception):
        pass

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


class DashboardSummaryResponse(BaseModel):
    total_documents: int = 0
    open_tasks: int = 0
    active_projects: int = 0
    last_ai_query_at: Optional[datetime] = None
    generated_at: datetime


def _is_undefined_table_error(exc: Exception) -> bool:
    """Detect undefined table errors across backends."""
    if isinstance(exc, AsyncpgUndefinedTableError):
        return True
    cause = getattr(exc, "__cause__", None)
    return isinstance(cause, AsyncpgUndefinedTableError)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_summary(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    tenant_id = ctx.tenant_id

    async def _safe_scalar(default: int | None, stmt):
        try:
            return await db.scalar(stmt) or default
        except (ProgrammingError, AsyncpgUndefinedTableError):
            return default
        except DBAPIError as exc:
            if _is_undefined_table_error(exc):
                return default
            raise

    document_count = await _safe_scalar(
        0,
        select(func.count()).select_from(Document).where(
            Document.tenant_id == tenant_id, Document.deleted_at.is_(None)
        ),
    )

    open_task_statuses = (TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value, TaskStatus.BLOCKED.value)
    open_task_count = await _safe_scalar(
        0,
        select(func.count())
        .select_from(Task)
        .where(
            Task.tenant_id == tenant_id,
            Task.status.in_(open_task_statuses),
            Task.deleted_at.is_(None),
        ),
    )

    active_project_count = await _safe_scalar(
        0,
        select(func.count()).select_from(ProcessingActivity).where(ProcessingActivity.tenant_id == tenant_id),
    )

    last_ai_query = await _safe_scalar(
        None,
        select(AuditLog.created_at)
        .where(AuditLog.tenant_id == tenant_id, AuditLog.entity_type == "ai_call")
        .order_by(AuditLog.created_at.desc())
        .limit(1),
    )

    return DashboardSummaryResponse(
        total_documents=document_count,
        open_tasks=open_task_count,
        active_projects=active_project_count,
        last_ai_query_at=last_ai_query,
        generated_at=datetime.utcnow(),
    )
