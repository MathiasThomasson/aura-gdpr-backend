from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_run import AuditRun
from app.db.models.billing_invoice import BillingInvoice
from app.db.models.document import Document
from app.db.models.dsr import DataSubjectRequest
from app.db.models.tenant_plan import TenantPlan
from app.schemas.billing import BillingInvoiceRead, BillingPlanRead, BillingUsageRead

DEFAULT_FEATURES = {
    "free": ["Basic DSR tracking", "AI summaries (limited)", "1 project"],
    "basic": ["Unlimited documents", "DSR workflows", "AI audit (monthly)", "Email notifications"],
    "pro": ["Advanced automation", "Custom policies", "Priority support", "AI audit weekly"],
    "enterprise": ["Custom SLAs", "Dedicated support", "Unlimited AI runs", "SSO"],
}


async def _get_or_create_plan(db: AsyncSession, tenant_id: int) -> TenantPlan:
    res = await db.execute(select(TenantPlan).where(TenantPlan.tenant_id == tenant_id))
    plan = res.scalars().first()
    if not plan:
        plan = TenantPlan(
            tenant_id=tenant_id,
            plan_type="free",
            name="Free",
            price_per_month=0,
            currency="USD",
            is_trial=True,
            trial_ends_at=datetime.now(timezone.utc),
            features=DEFAULT_FEATURES["free"],
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
    return plan


async def get_plan(db: AsyncSession, tenant_id: int) -> BillingPlanRead:
    plan = await _get_or_create_plan(db, tenant_id)
    trial_days_left = None
    if plan.trial_ends_at:
        delta = plan.trial_ends_at - datetime.now(timezone.utc)
        trial_days_left = max(0, int(delta.days))
    features_raw = plan.features or DEFAULT_FEATURES.get(plan.plan_type, [])
    if isinstance(features_raw, str):
        try:
            import json

            features_raw = json.loads(features_raw)
        except Exception:
            features_raw = [features_raw]
    features = list(features_raw)
    return BillingPlanRead(
        type=plan.plan_type,
        name=plan.name,
        price_per_month=plan.price_per_month,
        currency=plan.currency,
        is_trial=plan.is_trial,
        trial_days_left=trial_days_left,
        features=list(features),
    )


async def get_usage(db: AsyncSession, tenant_id: int) -> BillingUsageRead:
    now = datetime.now(timezone.utc)
    start_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    dsr_q = select(func.count()).select_from(
        select(DataSubjectRequest.id)
        .where(DataSubjectRequest.tenant_id == tenant_id, DataSubjectRequest.created_at >= start_month)
        .subquery()
    )
    dsr_count = (await db.execute(dsr_q)).scalar_one()

    doc_total = (await db.execute(
        select(func.count()).select_from(
            select(Document.id).where(Document.tenant_id == tenant_id, Document.deleted_at.is_(None)).subquery()
        )
    )).scalar_one()

    policies = (await db.execute(
        select(func.count()).select_from(
            select(Document.id)
            .where(
                Document.tenant_id == tenant_id,
                Document.deleted_at.is_(None),
                and_(Document.category.isnot(None), Document.category.ilike("%policy%")),
            )
            .subquery()
        )
    )).scalar_one()

    ai_calls = (await db.execute(
        select(func.count()).select_from(
            select(AuditRun.id).where(AuditRun.tenant_id == tenant_id, AuditRun.created_at >= start_month).subquery()
        )
    )).scalar_one()

    return BillingUsageRead(
        dsr_count_month=dsr_count,
        documents_count=doc_total,
        policies_count=policies,
        ai_calls_month=ai_calls,
    )


async def list_invoices(db: AsyncSession, tenant_id: int) -> List[BillingInvoice]:
    res = await db.execute(
        select(BillingInvoice).where(BillingInvoice.tenant_id == tenant_id).order_by(BillingInvoice.created_at.desc())
    )
    return res.scalars().all()


async def get_invoice_reads(invoices: List[BillingInvoice]) -> List[BillingInvoiceRead]:
    return [
        BillingInvoiceRead(
            id=inv.id,
            date=inv.created_at,
            amount=inv.amount,
            currency=inv.currency,
            description=inv.description,
            status=inv.status,
            invoice_url=inv.invoice_url,
        )
        for inv in invoices
    ]


async def ensure_invoice_exists(db: AsyncSession, tenant_id: int) -> None:
    """Create a stub invoice if tenant has none so UI has data."""
    res = await db.execute(select(func.count()).select_from(
        select(BillingInvoice.id).where(BillingInvoice.tenant_id == tenant_id).subquery()
    ))
    if res.scalar_one() == 0:
        invoice = BillingInvoice(
            tenant_id=tenant_id,
            amount=0,
            currency="USD",
            description="Trial invoice",
            status="paid",
            invoice_url=f"https://billing.example.com/invoice/{tenant_id}",
            created_at=datetime.now(timezone.utc),
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)


async def require_billing_access(role: str) -> None:
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient privileges for billing")
