from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_platform_admin
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


@router.get("/overview", response_model=PlatformOverviewResponse, dependencies=[Depends(get_platform_admin)])
async def platform_overview(db: AsyncSession = Depends(get_db)) -> PlatformOverviewResponse:
    total_tenants = (await db.execute(select(func.count()).select_from(Tenant))).scalar_one()
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_dsrs = (await db.execute(select(func.count()).select_from(DataSubjectRequest))).scalar_one()
    # DPIA table not present yet; keep stubbed count
    total_dpias = 0
    return PlatformOverviewResponse(
        total_tenants=total_tenants,
        total_users=total_users,
        total_dsrs=total_dsrs,
        total_dpias=total_dpias,
    )


@router.get("/tenants", response_model=list[PlatformTenantListItem], dependencies=[Depends(get_platform_admin)])
async def list_tenants(db: AsyncSession = Depends(get_db)) -> list[PlatformTenantListItem]:
    res = await db.execute(select(Tenant))
    tenants = res.scalars().all()
    return [
        PlatformTenantListItem(
            id=t.id,
            name=t.name,
            plan=getattr(t, "plan", "free") or "free",
            status=getattr(t, "status", "active") or "active",
            created_at=t.created_at,
        )
        for t in tenants
    ]


@router.get(
    "/tenants/{tenant_id}",
    response_model=PlatformTenantDetailResponse,
    dependencies=[Depends(get_platform_admin)],
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
