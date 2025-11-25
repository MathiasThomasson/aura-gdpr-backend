from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.db.models.task import Task
from app.models.task import TaskCreate, TaskOut, TaskUpdate
from app.core.auth import get_current_user
from app.core.audit import log_event

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskOut)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    task = Task(
        tenant_id=current_user.tenant_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status or "open",
        category=payload.category,
        assigned_to_user_id=payload.assigned_to_user_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    # audit log
    await log_event(db, current_user.tenant_id, current_user.id, "task", task.id, "create", None)
    return task


@router.get("/", response_model=list[TaskOut])
async def list_tasks(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user), limit: int = 50, offset: int = 0):
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    result = await db.execute(
        select(Task)
        .where(Task.tenant_id == current_user.tenant_id)
        .order_by(Task.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = result.scalars().all()
    return items


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.tenant_id == current_user.tenant_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.tenant_id == current_user.tenant_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(task, field, val)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await log_event(db, current_user.tenant_id, current_user.id, "task", task.id, "update", None)
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.tenant_id == current_user.tenant_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    await log_event(db, current_user.tenant_id, current_user.id, "task", task_id, "delete", None)
    return {"ok": True}
