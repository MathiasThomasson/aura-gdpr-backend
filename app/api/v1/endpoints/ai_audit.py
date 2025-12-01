from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.ai_audit import AuditRunListResponse, AuditRunRead
from app.services.ai_audit import get_latest_audit, list_audit_history, run_audit

router = APIRouter(prefix="/api/ai/audit", tags=["AI Audit"])


def _to_read(run) -> AuditRunRead:
    raw = run.raw_result or {}
    return AuditRunRead(
        id=run.id,
        created_at=run.created_at,
        completed_at=run.completed_at,
        overall_score=run.overall_score,
        areas=raw.get("areas", []),
        recommendations=raw.get("recommendations", []),
    )


@router.get("/latest", response_model=AuditRunRead)
async def get_latest(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    run = await get_latest_audit(db, ctx.tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="No audit runs yet")
    return _to_read(run)


@router.get("/history", response_model=AuditRunListResponse)
async def history(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    runs, total = await list_audit_history(db, ctx.tenant_id, skip, limit)
    return AuditRunListResponse(items=[_to_read(r) for r in runs], total=total)


@router.post("/run", response_model=AuditRunRead, status_code=201)
async def run(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    run_obj = await run_audit(db, ctx.tenant_id)
    return _to_read(run_obj)
