from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models.processing_activity import ProcessingActivity
from app.models.processing_activity import ProcessingActivityCreate, ProcessingActivityOut, ProcessingActivityUpdate
from app.core.audit import log_event

router = APIRouter(prefix="/api/processing_activities", tags=["ProcessingActivities"])


@router.post("/", response_model=ProcessingActivityOut)
async def create_processing_activity(payload: ProcessingActivityCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # tenant-scoped create
    pa = ProcessingActivity(tenant_id=current_user.tenant_id, name=payload.name, description=payload.description)
    db.add(pa)
    await db.commit()
    await db.refresh(pa)
    await log_event(db, current_user.tenant_id, current_user.id, "processing_activity", pa.id, "create", None)
    return pa


@router.get("/", response_model=list[ProcessingActivityOut])
async def list_processing_activities(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user), limit: int = 50, offset: int = 0):
    # list only for current user's tenant with pagination
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    result = await db.execute(
        select(ProcessingActivity)
        .where(ProcessingActivity.tenant_id == current_user.tenant_id)
        .order_by(ProcessingActivity.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = result.scalars().all()
    return items


@router.get("/{pa_id}", response_model=ProcessingActivityOut)
async def get_processing_activity(pa_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ProcessingActivity).where(ProcessingActivity.id == pa_id, ProcessingActivity.tenant_id == current_user.tenant_id))
    pa = result.scalars().first()
    if not pa:
        raise HTTPException(status_code=404, detail="ProcessingActivity not found")
    return pa


@router.put("/{pa_id}", response_model=ProcessingActivityOut)
async def update_processing_activity(pa_id: int, payload: ProcessingActivityUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # Ensure exists and tenant match
    result = await db.execute(select(ProcessingActivity).where(ProcessingActivity.id == pa_id, ProcessingActivity.tenant_id == current_user.tenant_id))
    pa = result.scalars().first()
    if not pa:
        raise HTTPException(status_code=404, detail="ProcessingActivity not found")

    if payload.name is not None:
        pa.name = payload.name
    if payload.description is not None:
        pa.description = payload.description

    db.add(pa)
    await db.commit()
    await db.refresh(pa)
    await log_event(db, current_user.tenant_id, current_user.id, "processing_activity", pa.id, "update", None)
    return pa


@router.delete("/{pa_id}")
async def delete_processing_activity(pa_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ProcessingActivity).where(ProcessingActivity.id == pa_id, ProcessingActivity.tenant_id == current_user.tenant_id))
    pa = result.scalars().first()
    if not pa:
        raise HTTPException(status_code=404, detail="ProcessingActivity not found")
    await db.delete(pa)
    await db.commit()
    await log_event(db, current_user.tenant_id, current_user.id, "processing_activity", pa_id, "delete", None)
    return {"ok": True}
