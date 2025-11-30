import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.db.models.dsr import DataSubjectRequest
from app.schemas.dsr import ALLOWED_DSR_STATUSES, DSRCreate, DSROut, DSRUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dsr", tags=["DSR"])

FINAL_STATUSES = {"completed", "rejected"}


async def _get_dsr_or_404(db: AsyncSession, tenant_id: int, dsr_id: int) -> DataSubjectRequest:
    dsr = await db.scalar(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == dsr_id,
            DataSubjectRequest.tenant_id == tenant_id,
            DataSubjectRequest.deleted_at.is_(None),
        )
    )
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")
    return dsr


@router.get("/", response_model=list[DSROut])
async def list_dsrs(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    try:
        result = await db.execute(
            select(DataSubjectRequest)
            .where(DataSubjectRequest.tenant_id == ctx.tenant_id, DataSubjectRequest.deleted_at.is_(None))
            .order_by(DataSubjectRequest.received_at.desc())
        )
        return result.scalars().all()
    except Exception:
        try:
            logger.exception("Failed to list DSRs; returning empty list")
        except Exception:
            pass
    return []


@router.post("/", response_model=DSROut, status_code=201)
async def create_dsr(
    payload: DSRCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    if payload.status not in ALLOWED_DSR_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    completed_at = datetime.utcnow() if payload.status in FINAL_STATUSES else None
    dsr = DataSubjectRequest(
        tenant_id=ctx.tenant_id,
        type=payload.type,
        data_subject=payload.data_subject,
        email=payload.email,
        status=payload.status,
        received_at=payload.received_at or datetime.utcnow(),
        due_at=payload.due_at,
        completed_at=completed_at,
        notes=payload.notes,
        deleted_at=None,
    )
    db.add(dsr)
    await db.commit()
    await db.refresh(dsr)
    return dsr


@router.patch("/{dsr_id}", response_model=DSROut)
async def update_dsr(
    dsr_id: int,
    payload: DSRUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    dsr = await _get_dsr_or_404(db, ctx.tenant_id, dsr_id)

    if payload.status is not None:
        if payload.status not in ALLOWED_DSR_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        new_status = payload.status
        status_changed = dsr.status != new_status
        dsr.status = new_status
        if new_status in FINAL_STATUSES:
            if status_changed or dsr.completed_at is None:
                dsr.completed_at = datetime.utcnow()
        else:
            dsr.completed_at = None

    if payload.notes is not None:
        dsr.notes = payload.notes

    if payload.due_at is not None:
        dsr.due_at = payload.due_at

    db.add(dsr)
    await db.commit()
    await db.refresh(dsr)
    return dsr
