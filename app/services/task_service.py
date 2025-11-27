from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.models.task_status import TaskStatus, ALLOWED_TASK_STATUSES
from app.repositories.task_repository import (
    create_task as repo_create_task,
    delete_task as repo_delete_task,
    get_task as repo_get_task,
    list_tasks as repo_list_tasks,
    save_task as repo_save_task,
)


async def _validate_assignee(db: AsyncSession, tenant_id: int, assignee_id: Optional[int]) -> None:
    if not assignee_id:
        return
    user = await db.get(User, assignee_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="Assigned user not in tenant")


async def create_task(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    title: str,
    description: Optional[str],
    due_date: Optional[datetime],
    status: Optional[str],
    category: Optional[str],
    assigned_to_user_id: Optional[int],
):
    await _validate_assignee(db, tenant_id, assigned_to_user_id)
    status_final = status or TaskStatus.OPEN.value
    return await repo_create_task(
        db=db,
        tenant_id=tenant_id,
        title=title,
        description=description,
        due_date=due_date,
        status=status_final,
        category=category,
        assigned_to_user_id=assigned_to_user_id,
    )


async def list_tasks(
    db: AsyncSession,
    tenant_id: int,
    limit: int,
    offset: int,
    status: Optional[str],
    due_before: Optional[datetime],
    due_after: Optional[datetime],
    assigned_to_user_id: Optional[int],
):
    if status and status not in ALLOWED_TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status filter")
    return await repo_list_tasks(
        db=db,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        status=status,
        due_before=due_before,
        due_after=due_after,
        assigned_to_user_id=assigned_to_user_id,
    )


async def get_task(db: AsyncSession, tenant_id: int, task_id: int):
    task = await repo_get_task(db, tenant_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def update_task(
    db: AsyncSession,
    tenant_id: int,
    task_id: int,
    title: Optional[str],
    description: Optional[str],
    due_date: Optional[datetime],
    status: Optional[str],
    category: Optional[str],
    assigned_to_user_id: Optional[int],
):
    task = await get_task(db, tenant_id, task_id)
    if status and status not in ALLOWED_TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    await _validate_assignee(db, tenant_id, assigned_to_user_id)
    for field, val in {
        "title": title,
        "description": description,
        "due_date": due_date,
        "status": status,
        "category": category,
        "assigned_to_user_id": assigned_to_user_id,
    }.items():
        if val is not None:
            setattr(task, field, val)
    return await repo_save_task(db, task)


async def delete_task(db: AsyncSession, tenant_id: int, task_id: int):
    task = await get_task(db, tenant_id, task_id)
    await repo_delete_task(db, task)
    return task
