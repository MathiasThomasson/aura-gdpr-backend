from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.billing import BillingInvoiceListResponse, BillingInvoiceRead, BillingPlanRead, BillingUsageRead
from app.services.billing_service import (
    ensure_invoice_exists,
    get_invoice_reads,
    get_plan,
    get_usage,
    list_invoices,
    require_billing_access,
)

router = APIRouter(prefix="/api/billing", tags=["Billing"])


@router.get("/plan", response_model=BillingPlanRead)
async def get_plan_endpoint(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    await require_billing_access(ctx.role)
    return await get_plan(db, ctx.tenant_id)


@router.get("/usage", response_model=BillingUsageRead)
async def get_usage_endpoint(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    await require_billing_access(ctx.role)
    return await get_usage(db, ctx.tenant_id)


@router.get("/invoices", response_model=BillingInvoiceListResponse)
async def get_invoices_endpoint(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    await require_billing_access(ctx.role)
    await ensure_invoice_exists(db, ctx.tenant_id)
    invoices = await list_invoices(db, ctx.tenant_id)
    return BillingInvoiceListResponse(items=await get_invoice_reads(invoices), total=len(invoices))


@router.post("/portal")
async def open_portal(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    await require_billing_access(ctx.role)
    return {"url": f"https://billing.example.com/tenant/{ctx.tenant_id}"}
