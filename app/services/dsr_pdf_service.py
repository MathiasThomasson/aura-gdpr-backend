from datetime import datetime
from io import BytesIO
from typing import Any, List

from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tenant import Tenant
from app.repositories.dsr_repository import get_dsr_by_id


def _format_datetime(value: datetime | None) -> str:
    if not value:
        return "Not set"
    cleaned = value.replace(microsecond=0)
    try:
        return cleaned.isoformat()
    except Exception:
        return str(cleaned)


def _paragraph_styles() -> dict[str, ParagraphStyle]:
    title = ParagraphStyle(
        name="Title",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=12,
        textColor=colors.HexColor("#1f2937"),
    )
    subtitle = ParagraphStyle(
        name="Subtitle",
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=16,
    )
    label = ParagraphStyle(
        name="Label",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#374151"),
    )
    value = ParagraphStyle(
        name="Value",
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )
    return {"title": title, "subtitle": subtitle, "label": label, "value": value}


async def generate_dsr_pdf(db: AsyncSession, tenant_id: int, dsr_id: int) -> bytes:
    dsr = await get_dsr_by_id(db, tenant_id, dsr_id)
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")

    tenant: Tenant | None = await db.get(Tenant, tenant_id)
    tenant_display = tenant.name if tenant and getattr(tenant, "name", None) else f"Tenant {tenant_id}"

    styles = _paragraph_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        title="Data Subject Request",
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )

    def row(label: str, value: str) -> list[Any]:
        return [Paragraph(label, styles["label"]), Paragraph(value or "-", styles["value"])]

    summary_rows: list[list[Any]] = [
        row("Request ID", str(dsr.id)),
        row("Tenant", tenant_display),
        row("Request type", dsr.request_type),
        row("Subject name", dsr.subject_name),
        row("Subject email", dsr.subject_email or "Not provided"),
        row("Description", dsr.description or "Not provided"),
        row("Priority", dsr.priority),
        row("Status", dsr.status),
        row("Deadline", _format_datetime(dsr.deadline)),
        row("Created at", _format_datetime(dsr.created_at)),
        row("Source", dsr.source),
    ]

    table = Table(summary_rows, colWidths=[2.1 * inch, 4.4 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements: List[Any] = [
        Paragraph("Data Subject Request", styles["title"]),
        Paragraph("Summary of the request for your records.", styles["subtitle"]),
        table,
    ]

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
