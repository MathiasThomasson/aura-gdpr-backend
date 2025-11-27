from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.db.models.processing_activity import ProcessingActivity
from app.models.processing_activity import ProcessingActivityCreate, ProcessingActivityOut, ProcessingActivityUpdate
from app.services.processing_activity_service import (
    create_processing_activity as svc_create,
    delete_processing_activity as svc_delete,
    get_processing_activity as svc_get,
    list_processing_activities as svc_list,
    update_processing_activity as svc_update,
)

router = APIRouter(prefix="/api/processing_activities", tags=["ProcessingActivities"])


@router.post("/", response_model=ProcessingActivityOut)
async def create_processing_activity(payload: ProcessingActivityCreate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    # tenant-scoped create
    pa = await svc_create(db, ctx.tenant_id, payload.name, payload.description)
    await log_event(db, ctx.tenant_id, ctx.user.id, "processing_activity", pa.id, "create", None)
    return pa


@router.get("/", response_model=list[ProcessingActivityOut])
async def list_processing_activities(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context), limit: int = 50, offset: int = 0):
    # list only for current user's tenant with pagination
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    result = await db.execute(
        select(ProcessingActivity)
        .where(ProcessingActivity.tenant_id == ctx.tenant_id)
        .order_by(ProcessingActivity.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return await svc_list(db, ctx.tenant_id, limit, offset)


@router.get("/{pa_id}", response_model=ProcessingActivityOut)
async def get_processing_activity(pa_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    return await svc_get(db, ctx.tenant_id, pa_id)


@router.put("/{pa_id}", response_model=ProcessingActivityOut)
async def update_processing_activity(pa_id: int, payload: ProcessingActivityUpdate, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    # Ensure exists and tenant match
    result = await db.execute(select(ProcessingActivity).where(ProcessingActivity.id == pa_id, ProcessingActivity.tenant_id == ctx.tenant_id))
    pa = await svc_update(db, ctx.tenant_id, pa_id, payload.name, payload.description)
    await log_event(db, ctx.tenant_id, ctx.user.id, "processing_activity", pa.id, "update", None)
    return pa


@router.delete("/{pa_id}")
async def delete_processing_activity(pa_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    pa = await svc_delete(db, ctx.tenant_id, pa_id)
    await log_event(db, ctx.tenant_id, ctx.user.id, "processing_activity", pa_id, "delete", None)
    return {"ok": True}
