from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.db.models.incident import Incident
from app.schemas.incidents import IncidentCreate, IncidentOut
from app.services.email import send_templated_email

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("", response_model=list[IncidentOut], summary="List incidents", description="List incidents for the current tenant.")
async def list_incidents(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    result = await db.execute(select(Incident).where(Incident.tenant_id == ctx.tenant_id))
    return [IncidentOut.model_validate(inc) for inc in result.scalars().all()]


@router.post("", response_model=IncidentOut, status_code=201, summary="Create incident", description="Create an incident; high severity triggers an alert email.")
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    incident = Incident(tenant_id=ctx.tenant_id, title=payload.title, severity=payload.severity, status="open")
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    if payload.severity == "high":
        await send_templated_email(
            to=ctx.user.email,
            subject="Incident alert",
            template="incident_alert_en.txt",
            context={
                "organization_name": str(ctx.tenant_id),
                "recipient_name": ctx.user.email,
                "link": "https://app.example.com/incidents",
                "incident_title": payload.title,
            },
        )
    return IncidentOut.model_validate(incident)
