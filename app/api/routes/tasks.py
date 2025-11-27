from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.models.task import TaskCreate, TaskOut, TaskUpdate
from app.models.task_status import TaskStatus
from app.services.task_service import (
    create_task as svc_create_task,
    delete_task as svc_delete_task,
    get_task as svc_get_task,
    list_tasks as svc_list_tasks,
    update_task as svc_update_task,
)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskOut)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    task = await svc_create_task(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status,
        category=payload.category,
        assigned_to_user_id=payload.assigned_to_user_id,
    )
    # audit log
    await log_event(db, ctx.tenant_id, ctx.user.id, "task", task.id, "create", None)
    return task


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    assigned_to_user_id: int | None = None,
):
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    items = await svc_list_tasks(
        db=db,
        tenant_id=ctx.tenant_id,
        limit=limit,
        offset=offset,
        status=status,
        due_before=due_before,
        due_after=due_after,
        assigned_to_user_id=assigned_to_user_id,
    )
    return items


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    return await svc_get_task(db, ctx.tenant_id, task_id)


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    updated = await svc_update_task(
        db=db,
        tenant_id=ctx.tenant_id,
        task_id=task_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status,
        category=payload.category,
        assigned_to_user_id=payload.assigned_to_user_id,
    )
    await log_event(db, ctx.tenant_id, ctx.user.id, "task", updated.id, "update", None)
    return updated


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    task = await svc_delete_task(db, ctx.tenant_id, task_id)
    await log_event(db, ctx.tenant_id, ctx.user.id, "task", task_id, "delete", None)
    return {"ok": True}
