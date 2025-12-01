from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_run import AuditRun
from app.db.models.document import Document
from app.db.models.dsr import DataSubjectRequest


async def _count(db: AsyncSession, stmt):
    return (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()


def _build_mock_result(document_count: int, dsr_count: int, ai_runs: int) -> Dict[str, Any]:
    base_score = 70
    penalty = min(dsr_count * 2, 20)
    reward = min(document_count, 10)
    stability = 5 if ai_runs > 0 else 0
    overall = max(40, min(95, base_score - penalty + reward + stability))

    areas: List[Dict[str, Any]] = [
        {"name": "Documentation", "score": min(100, 60 + reward * 2), "findings": [f"{document_count} documents tracked"]},
        {"name": "DSR Handling", "score": max(30, 80 - penalty), "findings": [f"{dsr_count} open requests impact SLA"]},
        {"name": "Automation", "score": 50 + stability, "findings": [f"{ai_runs} AI runs executed this month"]},
    ]
    recommendations = [
        {"title": "Tighten DSR process", "detail": "Reduce open DSRs by assigning owners and due dates."},
        {"title": "Expand documentation", "detail": "Add policies and DPIAs to improve compliance coverage."},
    ]
    return {"overall_score": overall, "areas": areas, "recommendations": recommendations}


async def run_audit(db: AsyncSession, tenant_id: int) -> AuditRun:
    doc_stmt = select(Document.id).where(Document.tenant_id == tenant_id, Document.deleted_at.is_(None))
    dsr_stmt = select(DataSubjectRequest.id).where(DataSubjectRequest.tenant_id == tenant_id)
    audit_stmt = select(AuditRun.id).where(AuditRun.tenant_id == tenant_id)

    doc_count = await _count(db, doc_stmt)
    dsr_count = await _count(db, dsr_stmt)
    audit_count = await _count(db, audit_stmt)

    payload = _build_mock_result(doc_count, dsr_count, audit_count)
    now = datetime.now(timezone.utc)
    run = AuditRun(
        tenant_id=tenant_id,
        created_at=now,
        completed_at=now,
        overall_score=payload["overall_score"],
        raw_result=payload,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def get_latest_audit(db: AsyncSession, tenant_id: int) -> AuditRun | None:
    res = await db.execute(
        select(AuditRun).where(AuditRun.tenant_id == tenant_id).order_by(AuditRun.created_at.desc()).limit(1)
    )
    return res.scalars().first()


async def list_audit_history(db: AsyncSession, tenant_id: int, skip: int, limit: int) -> tuple[List[AuditRun], int]:
    base = select(AuditRun).where(AuditRun.tenant_id == tenant_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    res = await db.execute(base.order_by(AuditRun.created_at.desc()).offset(skip).limit(limit))
    return res.scalars().all(), total
