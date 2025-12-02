from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.models.task import TaskCreate, TaskOut, TaskUpdate
from app.services.task_service import (
    create_task as svc_create_task,
    delete_task as svc_delete_task,
    get_task as svc_get_task,
    list_tasks as svc_list_tasks,
    update_task as svc_update_task,
)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.post("", response_model=TaskOut)
async def create_task(
    payload: TaskCreate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)
):
    return await svc_create_task(
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


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    assigned_to_user_id: int | None = None,
):
    return await svc_list_tasks(
        db=db,
        tenant_id=ctx.tenant_id,
        limit=limit,
        offset=offset,
        status=status,
        due_before=due_before,
        due_after=due_after,
        assigned_to_user_id=assigned_to_user_id,
    )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    return await svc_get_task(db, ctx.tenant_id, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)
):
    return await svc_update_task(
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


@router.put("/{task_id}", response_model=TaskOut)
async def replace_task(
    task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)
):
    return await update_task(task_id, payload, db=db, ctx=ctx)


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    await svc_delete_task(db, ctx.tenant_id, task_id)
    return {"ok": True}
