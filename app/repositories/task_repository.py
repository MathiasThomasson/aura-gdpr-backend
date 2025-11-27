from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.task import Task


async def create_task(
    db: AsyncSession,
    tenant_id: int,
    title: str,
    description: Optional[str],
    due_date: Optional[datetime],
    status: str,
    category: Optional[str],
    assigned_to_user_id: Optional[int],
) -> Task:
    task = Task(
        tenant_id=tenant_id,
        title=title,
        description=description,
        due_date=due_date,
        status=status,
        category=category,
        assigned_to_user_id=assigned_to_user_id,
        deleted_at=None,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession,
    tenant_id: int,
    limit: int,
    offset: int,
    status: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    assigned_to_user_id: Optional[int] = None,
) -> List[Task]:
    filters = [Task.tenant_id == tenant_id, Task.deleted_at.is_(None)]
    if status:
        filters.append(Task.status == status)
    if due_before:
        filters.append(Task.due_date <= due_before)
    if due_after:
        filters.append(Task.due_date >= due_after)
    if assigned_to_user_id:
        filters.append(Task.assigned_to_user_id == assigned_to_user_id)

    stmt = (
        select(Task)
        .where(and_(*filters))
        .order_by(Task.id.desc())
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


async def get_task(db: AsyncSession, tenant_id: int, task_id: int) -> Optional[Task]:
    res = await db.execute(select(Task).where(Task.id == task_id, Task.tenant_id == tenant_id, Task.deleted_at.is_(None)))
    return res.scalars().first()


async def save_task(db: AsyncSession, task: Task) -> Task:
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    task.deleted_at = datetime.utcnow()
    db.add(task)
    await db.commit()
