import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.core.deps import CurrentContext, current_context
from app.core.config import settings
from app.db.database import get_db
from app.db.models.dsr import DataSubjectRequest
from app.db.models.dsr_status_history import DSRStatusHistory
from app.db.models.tenant_dsr_settings import TenantDSRSettings
from app.middleware.rate_limit import rate_limit
from app.schemas.dsr import ALLOWED_DSR_STATUSES, DSRCreate, DSROut, DSRStatusChange, DSRUpdate
from app.schemas.dsr import ALLOWED_DSR_PRIORITIES, PublicDSRCreate
from app.services.email import send_templated_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dsr", tags=["DSR"])
public_router = APIRouter(prefix="/api/public/dsr", tags=["DSR Public"])

FINAL_STATUSES = {"completed", "rejected"}


def _parse_status_filters(raw_status: Optional[list[str]]) -> list[str]:
    if not raw_status:
        return []
    statuses: list[str] = []
    for item in raw_status:
        parts = [p.strip() for p in item.split(",") if p.strip()]
        statuses.extend(parts)
    # Preserve order while deduplicating
    seen: set[str] = set()
    unique_statuses: list[str] = []
    for status in statuses:
        if status not in seen:
            seen.add(status)
            unique_statuses.append(status)
    return unique_statuses


async def _ensure_status_history_table(db: AsyncSession) -> None:
    await db.run_sync(
        lambda sync_session: DSRStatusHistory.__table__.create(
            bind=sync_session.get_bind(), checkfirst=True  # type: ignore[arg-type]
        )
    )


async def _record_status_history(
    db: AsyncSession,
    dsr: DataSubjectRequest,
    from_status: str,
    to_status: str,
    changed_by_user_id: Optional[int],
    note: Optional[str],
) -> None:
    await _ensure_status_history_table(db)
    history = DSRStatusHistory(
        dsr_id=dsr.id,
        from_status=from_status,
        to_status=to_status,
        changed_by_user_id=changed_by_user_id,
        changed_at=datetime.utcnow(),
        note=note,
    )
    db.add(history)


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


async def _apply_status_change(
    db: AsyncSession,
    dsr: DataSubjectRequest,
    new_status: str,
    ctx: CurrentContext,
    note: Optional[str] = None,
    reject_same: bool = False,
) -> None:
    if new_status not in ALLOWED_DSR_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if dsr.status == new_status:
        if reject_same:
            raise HTTPException(status_code=400, detail="Status is unchanged")
        return
    if dsr.status in FINAL_STATUSES and new_status != dsr.status:
        raise HTTPException(status_code=400, detail=f"Cannot transition from final status {dsr.status}")

    previous_status = dsr.status
    dsr.status = new_status
    dsr.updated_at = datetime.utcnow()

    if new_status in FINAL_STATUSES:
        dsr.completed_at = datetime.utcnow()
        if dsr.subject_email:
            await send_templated_email(
                to=dsr.subject_email,
                subject="Your request is completed",
                template="dsr_completed_en.txt",
                context={
                    "recipient_name": dsr.subject_name,
                    "organization_name": str(ctx.tenant_id),
                    "link": "https://app.example.com/dsr",
                },
            )
    else:
        dsr.completed_at = None

    await _record_status_history(db, dsr, previous_status, new_status, getattr(ctx.user, "id", None), note)


def _public_base_url() -> str:
    if settings.PUBLIC_FRONTEND_URL:
        return settings.PUBLIC_FRONTEND_URL.rstrip("/")
    if settings.CORS_ORIGINS and settings.CORS_ORIGINS != "*":
        first_origin = settings.CORS_ORIGINS.split(",")[0].strip()
        if first_origin:
            return first_origin.rstrip("/")
    return "https://app.example.com"


def _serialize_public_link(config: TenantDSRSettings) -> dict[str, Optional[str]]:
    enabled = bool(config.public_dsr_enabled)
    key = config.public_dsr_key
    if not key:
        return {"enabled": False, "public_url": None}
    base_url = _public_base_url()
    url = f"{base_url}/public/dsr/{key}" if enabled else None
    return {"enabled": enabled, "public_url": url}


async def _ensure_public_settings_table(db: AsyncSession) -> None:
    bind = db.get_bind()
    dialect = getattr(bind, "dialect", None)
    if dialect and dialect.name.startswith("sqlite"):
        create_sql = """
        CREATE TABLE IF NOT EXISTS tenant_dsr_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            public_dsr_key VARCHAR(64),
            public_dsr_enabled BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_tenant_dsr_settings_tenant UNIQUE (tenant_id),
            CONSTRAINT uq_tenant_dsr_settings_key UNIQUE (public_dsr_key),
            FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """
        await db.execute(text(create_sql))
        await db.commit()
    else:
        await db.run_sync(lambda conn: TenantDSRSettings.__table__.create(bind=conn, checkfirst=True))
        await db.commit()


async def _get_or_create_public_config(db: AsyncSession, tenant_id: int) -> TenantDSRSettings:
    await _ensure_public_settings_table(db)
    config = await db.scalar(select(TenantDSRSettings).where(TenantDSRSettings.tenant_id == tenant_id))
    if config:
        return config
    config = TenantDSRSettings(tenant_id=tenant_id, public_dsr_enabled=False, public_dsr_key=None)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/", response_model=list[DSROut], summary="List DSRs", description="List data subject requests for the tenant with optional pagination.")
@rate_limit("public_dsr", limit=10, window_seconds=60)
async def list_dsrs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
    limit: int = 50,
    offset: int = 0,
    status: Optional[list[str]] = Query(None),
    overdue: bool = False,
):
    statuses = _parse_status_filters(status)
    invalid_statuses = [s for s in statuses if s not in ALLOWED_DSR_STATUSES]
    if invalid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    try:
        stmt = (
            select(DataSubjectRequest)
            .options(
                load_only(
                    DataSubjectRequest.id,
                    DataSubjectRequest.tenant_id,
                    DataSubjectRequest.request_type,
                    DataSubjectRequest.subject_name,
                    DataSubjectRequest.subject_email,
                    DataSubjectRequest.priority,
                    DataSubjectRequest.status,
                    DataSubjectRequest.received_at,
                    DataSubjectRequest.deadline,
                    DataSubjectRequest.completed_at,
                    DataSubjectRequest.description,
                    DataSubjectRequest.source,
                    DataSubjectRequest.created_at,
                    DataSubjectRequest.updated_at,
                    DataSubjectRequest.deleted_at,
                )
            )
            .where(DataSubjectRequest.tenant_id == ctx.tenant_id, DataSubjectRequest.deleted_at.is_(None))
        )

        if statuses:
            stmt = stmt.where(DataSubjectRequest.status.in_(statuses))

        if overdue:
            today = datetime.utcnow().date()
            stmt = stmt.where(
                DataSubjectRequest.deadline.is_not(None),
                func.date(DataSubjectRequest.deadline) < today,
                DataSubjectRequest.status != "completed",
            )

        stmt = stmt.order_by(DataSubjectRequest.received_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()
    except HTTPException:
        raise
    except Exception:
        try:
            logger.exception("Failed to list DSRs; returning empty list")
        except Exception:
            pass
    return []


@router.post("/", response_model=DSROut, status_code=201, summary="Create DSR", description="Create a data subject request.")
@rate_limit("public_dsr", limit=10, window_seconds=60)
async def create_dsr(
    payload: DSRCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    status = payload.status or "received"
    if status not in ALLOWED_DSR_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if payload.priority not in ALLOWED_DSR_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")

    created_at = payload.received_at or datetime.utcnow()
    received_at = payload.received_at or created_at
    deadline = payload.deadline or (created_at + timedelta(days=30))
    completed_at = datetime.utcnow() if status in FINAL_STATUSES else None
    dsr = DataSubjectRequest(
        tenant_id=ctx.tenant_id,
        request_type=payload.request_type,
        subject_name=payload.subject_name,
        subject_email=payload.subject_email,
        priority=payload.priority,
        status=status,
        received_at=received_at,
        deadline=deadline,
        completed_at=completed_at,
        description=payload.description,
        source=payload.source,
        deleted_at=None,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(dsr)
    await db.commit()
    await db.refresh(dsr)
    if payload.subject_email:
        await send_templated_email(
            to=payload.subject_email,
            subject="We received your request",
            template="dsr_received_en.txt",
            context={
                "recipient_name": payload.subject_name,
                "organization_name": str(ctx.tenant_id),
                "link": "https://app.example.com/dsr",
            },
        )
    return dsr


@router.patch("/{dsr_id}/status", response_model=DSROut, summary="Change DSR status", description="Update the status of a DSR and record history.")
async def change_dsr_status(
    dsr_id: int,
    payload: DSRStatusChange,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    dsr = await _get_dsr_or_404(db, ctx.tenant_id, dsr_id)
    await _apply_status_change(db, dsr, payload.status, ctx, note=payload.note, reject_same=True)
    db.add(dsr)
    await db.commit()
    await db.refresh(dsr)
    return dsr


@router.patch("/{dsr_id}", response_model=DSROut, summary="Update DSR", description="Update status, notes, or due date for a DSR.")
async def update_dsr(
    dsr_id: int,
    payload: DSRUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    dsr = await _get_dsr_or_404(db, ctx.tenant_id, dsr_id)

    if payload.status is not None:
        await _apply_status_change(db, dsr, payload.status, ctx)

    if payload.description is not None:
        dsr.description = payload.description

    if payload.deadline is not None:
        dsr.deadline = payload.deadline

    if payload.priority is not None:
        if payload.priority not in ALLOWED_DSR_PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")
        dsr.priority = payload.priority

    dsr.updated_at = datetime.utcnow()
    db.add(dsr)
    await db.commit()
    await db.refresh(dsr)
    return dsr


@router.get("/public-link", summary="Get public DSR link", description="Fetch the public DSR submission link for the current tenant.")
async def get_public_link(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    config = await _get_or_create_public_config(db, ctx.tenant_id)
    return _serialize_public_link(config)


@router.post("/public-link/enable", summary="Enable public DSR form", description="Enable the public DSR submission form for the current tenant.")
async def enable_public_link(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    config = await _get_or_create_public_config(db, ctx.tenant_id)
    if not config.public_dsr_key:
        config.public_dsr_key = uuid.uuid4().hex
    config.public_dsr_enabled = True
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return _serialize_public_link(config)


@router.post("/public-link/disable", summary="Disable public DSR form", description="Disable the public DSR submission form without deleting the key.")
async def disable_public_link(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    config = await _get_or_create_public_config(db, ctx.tenant_id)
    config.public_dsr_enabled = False
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return _serialize_public_link(config)


@public_router.post("/{public_key}", status_code=201, summary="Submit public DSR", description="Public submission endpoint for data subject requests.")
@rate_limit("public_dsr_submit", limit=5, window_seconds=60)
async def submit_public_dsr(
    public_key: str,
    payload: PublicDSRCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    config = await db.scalar(
        select(TenantDSRSettings).where(
            TenantDSRSettings.public_dsr_key == public_key,
            TenantDSRSettings.public_dsr_enabled.is_(True),
        )
    )
    if not config:
        raise HTTPException(status_code=404, detail="Public form not found")

    received_at = datetime.utcnow()
    deadline = received_at + timedelta(days=30)
    dsr = DataSubjectRequest(
        tenant_id=config.tenant_id,
        request_type=payload.request_type,
        subject_name=payload.subject_name,
        subject_email=payload.subject_email,
        description=payload.description,
        priority=payload.priority,
        status="received",
        source="public_form",
        received_at=received_at,
        deadline=deadline,
        created_at=received_at,
        updated_at=received_at,
    )
    db.add(dsr)
    await db.commit()
    await db.refresh(dsr)
    return {"id": dsr.id, "status": dsr.status, "deadline": dsr.deadline}
