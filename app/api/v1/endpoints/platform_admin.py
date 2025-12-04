from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_platform_owner
from app.core.config import settings
from app.db.database import get_db
from app.db.models.audit_log import AuditLog
from app.db.models.dsr import DataSubjectRequest
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.schemas.platform_admin import (
    PlatformOverviewResponse,
    PlatformTenantDetailResponse,
    PlatformTenantListItem,
)

router = APIRouter(prefix="/api/admin/platform", tags=["Platform Admin"])


@router.get("/overview", response_model=PlatformOverviewResponse, dependencies=[Depends(require_platform_owner)])
async def platform_overview(db: AsyncSession = Depends(get_db)) -> PlatformOverviewResponse:
    total_tenants = (await db.execute(select(func.count()).select_from(Tenant))).scalar_one()
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_dsrs = (await db.execute(select(func.count()).select_from(DataSubjectRequest))).scalar_one()
    # DPIA table not present yet; keep stubbed count
    total_dpias = 0
    # Active subscriptions/MRR placeholders until billing is wired
    active_subscriptions = total_tenants
    mrr_eur = float(total_tenants * 100)  # placeholder
    ai_tokens_30d = 0
    new_tenants_by_month: list[dict] = []
    ai_tokens_by_month: list[dict] = []
    try:
        result = await db.execute(
            text(
                "SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS count FROM tenants GROUP BY month ORDER BY month DESC LIMIT 12"
            )
        )
        new_tenants_by_month = [{"month": r[0], "count": r[1]} for r in result.fetchall() if r[0]]
    except Exception:
        pass

    system_health = {
        "backend": "ok",
        "database": "ok",
        "last_deploy": datetime.now(timezone.utc).isoformat(),
        "git_sha": getattr(settings, "BUILD_COMMIT", None) or getattr(settings, "BUILD", "dev"),
    }
    return PlatformOverviewResponse(
        total_tenants=total_tenants,
        total_users=total_users,
        total_dsrs=total_dsrs,
        total_dpias=total_dpias,
        active_subscriptions=active_subscriptions,
        mrr_eur=mrr_eur,
        ai_tokens_30d=ai_tokens_30d,
        new_tenants_by_month=new_tenants_by_month,
        ai_tokens_by_month=ai_tokens_by_month,
        system_health=system_health,
    )


@router.get("/tenants", response_model=list[PlatformTenantListItem], dependencies=[Depends(require_platform_owner)])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    plan: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[PlatformTenantListItem]:
    stmt = select(Tenant)
    if plan:
        stmt = stmt.where(Tenant.plan == plan)
    if status:
        stmt = stmt.where(Tenant.status == status)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(Tenant.name).like(like))
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    tenants = res.scalars().all()
    tenant_ids = [t.id for t in tenants]

    user_counts: dict[int, int] = {}
    if tenant_ids:
        counts_res = await db.execute(
            select(User.tenant_id, func.count()).where(User.tenant_id.in_(tenant_ids)).group_by(User.tenant_id)
        )
        user_counts = {tid: cnt for tid, cnt in counts_res.all()}

    return [
        PlatformTenantListItem(
            id=t.id,
            name=t.name,
            plan=getattr(t, "plan", "free") or "free",
            status=getattr(t, "status", "active") or "active",
            created_at=t.created_at,
            users=user_counts.get(t.id, 0),
            next_billing_date=None,
        )
        for t in tenants
    ]


@router.get(
    "/tenants/{tenant_id}",
    response_model=PlatformTenantDetailResponse,
    dependencies=[Depends(require_platform_owner)],
)
async def tenant_detail(tenant_id: int, db: AsyncSession = Depends(get_db)) -> PlatformTenantDetailResponse:
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    total_users = (await db.execute(select(func.count()).select_from(User).where(User.tenant_id == tenant_id))).scalar_one()
    total_dsrs = (
        await db.execute(
            select(func.count()).select_from(DataSubjectRequest).where(DataSubjectRequest.tenant_id == tenant_id)
        )
    ).scalar_one()
    total_dpias = 0

    last_activity = (
        await db.execute(
            select(AuditLog.created_at)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return PlatformTenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        plan=getattr(tenant, "plan", "free") or "free",
        status=getattr(tenant, "status", "active") or "active",
        created_at=tenant.created_at,
        total_users=total_users,
        total_dsrs=total_dsrs,
        total_dpias=total_dpias,
        last_activity_at=last_activity,
    )


@router.post("/tenants/{tenant_id}/suspend", dependencies=[Depends(require_platform_owner)])
async def suspend_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.status = "suspended"
    tenant.is_active = False
    db.add(tenant)
    await db.commit()
    return {"id": tenant.id, "status": tenant.status}


@router.post("/tenants/{tenant_id}/unsuspend", dependencies=[Depends(require_platform_owner)])
async def unsuspend_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.status = "active"
    tenant.is_active = True
    db.add(tenant)
    await db.commit()
    return {"id": tenant.id, "status": tenant.status}


@router.post("/tenants/{tenant_id}/impersonate", dependencies=[Depends(require_platform_owner)])
async def impersonate_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # Issue a placeholder one-time token for impersonation flows (to be wired to UI).
    token = f"impersonation-{tenant_id}-{int(datetime.now().timestamp())}"
    return {"token": token, "tenant_id": tenant_id}
