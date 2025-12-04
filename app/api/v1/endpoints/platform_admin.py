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
    PlatformUserItem,
    PlatformPlan,
    PlatformBillingStatus,
    PayPalConfig,
    PayPalWebhookEvent,
    AIUsageSummary,
    LogItem,
    JobStatus,
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


@router.get("/users", response_model=list[PlatformUserItem], dependencies=[Depends(require_platform_owner)])
async def list_users_platform(
    db: AsyncSession = Depends(get_db),
    email: str | None = Query(None),
    role: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[PlatformUserItem]:
    stmt = select(User, Tenant.name.label("tenant_name")).join(Tenant, User.tenant_id == Tenant.id, isouter=True)
    if email:
        like = f"%{email.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(like))
    if role:
        stmt = stmt.where(User.role == role)
    if status:
        stmt = stmt.where(User.status == status)
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    items: list[PlatformUserItem] = []
    for user, tenant_name in res.all():
        items.append(
            PlatformUserItem(
                id=user.id,
                email=user.email,
                role=user.role,
                tenant_id=user.tenant_id,
                tenant_name=tenant_name,
                last_login_at=getattr(user, "last_login_at", None),
                status=getattr(user, "status", "active") or "active",
            )
        )
    return items


@router.get("/users/{user_id}", response_model=PlatformUserItem, dependencies=[Depends(require_platform_owner)])
async def get_user_platform(user_id: int, db: AsyncSession = Depends(get_db)) -> PlatformUserItem:
    stmt = select(User, Tenant.name.label("tenant_name")).join(Tenant, User.tenant_id == Tenant.id, isouter=True).where(User.id == user_id)
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    user, tenant_name = row
    return PlatformUserItem(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
        last_login_at=getattr(user, "last_login_at", None),
        status=getattr(user, "status", "active") or "active",
    )


async def _set_user_status(user_id: int, status: str, db: AsyncSession) -> PlatformUserItem:
    stmt = select(User, Tenant.name.label("tenant_name")).join(Tenant, User.tenant_id == Tenant.id, isouter=True).where(User.id == user_id)
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    user, tenant_name = row
    user.status = status
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return PlatformUserItem(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
        last_login_at=getattr(user, "last_login_at", None),
        status=getattr(user, "status", "active") or "active",
    )


@router.post("/users/{user_id}/disable", response_model=PlatformUserItem, dependencies=[Depends(require_platform_owner)])
async def disable_user(user_id: int, db: AsyncSession = Depends(get_db)) -> PlatformUserItem:
    return await _set_user_status(user_id, "disabled", db)


@router.post("/users/{user_id}/enable", response_model=PlatformUserItem, dependencies=[Depends(require_platform_owner)])
async def enable_user(user_id: int, db: AsyncSession = Depends(get_db)) -> PlatformUserItem:
    return await _set_user_status(user_id, "active", db)


@router.get("/plans", response_model=list[PlatformPlan], dependencies=[Depends(require_platform_owner)])
async def list_plans() -> list[PlatformPlan]:
    return [
        PlatformPlan(
            id="free",
            name="Free",
            monthly_price_eur=0,
            yearly_price_eur=0,
            paypal_product_id=None,
            paypal_plan_id_monthly=None,
            paypal_plan_id_yearly=None,
            included_ai_tokens=1000,
            max_users=3,
            features=["dsr", "documents"],
        ),
        PlatformPlan(
            id="pro",
            name="Pro",
            monthly_price_eur=99,
            yearly_price_eur=999,
            paypal_product_id="prod_pro",
            paypal_plan_id_monthly="plan_pro_m",
            paypal_plan_id_yearly="plan_pro_y",
            included_ai_tokens=100000,
            max_users=50,
            features=["dsr", "documents", "ai_audit", "ropa", "dpia"],
        ),
    ]


@router.post("/plans", response_model=PlatformPlan, dependencies=[Depends(require_platform_owner)])
async def create_plan(plan: PlatformPlan) -> PlatformPlan:
    # Stub: echo back. Replace with persistence when available.
    return plan


@router.patch("/plans/{plan_id}", response_model=PlatformPlan, dependencies=[Depends(require_platform_owner)])
async def update_plan(plan_id: str, plan: PlatformPlan) -> PlatformPlan:
    # Stub: echo back with plan_id.
    return plan


@router.get("/tenants/{tenant_id}/billing", response_model=PlatformBillingStatus, dependencies=[Depends(require_platform_owner)])
async def tenant_billing(tenant_id: int, db: AsyncSession = Depends(get_db)) -> PlatformBillingStatus:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return PlatformBillingStatus(
        tenant_id=tenant.id,
        plan=getattr(tenant, "plan", "free") or "free",
        billing_cycle="monthly",
        next_payment_date=None,
        paypal_subscription_id=None,
        status=getattr(tenant, "status", "active") or "active",
        payment_history=[],
    )


@router.post("/tenants/{tenant_id}/billing/resync", dependencies=[Depends(require_platform_owner)])
async def tenant_billing_resync(tenant_id: int) -> dict:
    return {"tenant_id": tenant_id, "status": "resync_requested"}


@router.get("/paypal/config", response_model=PayPalConfig, dependencies=[Depends(require_platform_owner)])
async def paypal_config() -> PayPalConfig:
    return PayPalConfig(mode="sandbox", client_id_masked="****", webhook_id=None)


@router.post("/paypal/config", response_model=PayPalConfig, dependencies=[Depends(require_platform_owner)])
async def paypal_config_save(config: PayPalConfig) -> PayPalConfig:
    return config


@router.post("/paypal/test-connection", dependencies=[Depends(require_platform_owner)])
async def paypal_test_connection() -> dict:
    return {"status": "ok", "message": "Test connection not implemented (stub)."}


@router.get("/paypal/webhook-events", response_model=list[PayPalWebhookEvent], dependencies=[Depends(require_platform_owner)])
async def paypal_webhook_events() -> list[PayPalWebhookEvent]:
    now = datetime.now(timezone.utc)
    return [
        PayPalWebhookEvent(
          event_id="evt_1",
          event_type="subscription.created",
          status="processed",
          received_at=now,
          tenant_id=None,
          message=None,
        )
    ]


@router.get("/ai/usage", response_model=AIUsageSummary, dependencies=[Depends(require_platform_owner)])
async def ai_usage_summary() -> AIUsageSummary:
    return AIUsageSummary(
        tokens_24h=0,
        tokens_7d=0,
        tokens_30d=0,
        cost_eur_estimate=0.0,
        items=[],
    )


@router.get("/ai/usage/{tenant_id}", response_model=AIUsageSummary, dependencies=[Depends(require_platform_owner)])
async def ai_usage_tenant(tenant_id: int) -> AIUsageSummary:
    return AIUsageSummary(
        tokens_24h=0,
        tokens_7d=0,
        tokens_30d=0,
        cost_eur_estimate=0.0,
        items=[],
    )


@router.post("/ai/limits/{tenant_id}", dependencies=[Depends(require_platform_owner)])
async def ai_limits_update(tenant_id: int, payload: dict) -> dict:
    return {"tenant_id": tenant_id, "saved": True, "payload": payload}


@router.get("/logs", response_model=list[LogItem], dependencies=[Depends(require_platform_owner)])
async def platform_logs(
    db: AsyncSession = Depends(get_db),
    level: str | None = Query(None),
    service: str | None = Query(None),
    tenant_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[LogItem]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if tenant_id:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    res = await db.execute(stmt)
    logs: list[LogItem] = []
    for log in res.scalars().all():
        logs.append(
            LogItem(
                timestamp=getattr(log, "created_at", datetime.now(timezone.utc)),
                level="INFO",
                service="backend",
                tenant_id=getattr(log, "tenant_id", None),
                message=getattr(log, "action", "event"),
                details=None,
            )
        )
    return logs


@router.get("/jobs", response_model=list[JobStatus], dependencies=[Depends(require_platform_owner)])
async def platform_jobs() -> list[JobStatus]:
    now = datetime.now(timezone.utc)
    return [
        JobStatus(name="Monthly Compliance Report Job", last_run=now, status="ok", message=None),
        JobStatus(name="DSR Deadline Checker Job", last_run=now, status="ok", message=None),
        JobStatus(name="Backup Job", last_run=now, status="ok", message=None),
    ]
