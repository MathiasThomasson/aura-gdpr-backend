from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.incidents import IncidentCreate, IncidentOut, IncidentUpdate
from app.services.incident_service import (
    create_incident,
    delete_incident,
    get_incident,
    list_incidents,
    update_incident,
)

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("", response_model=list[IncidentOut], summary="List incidents", description="List incidents for the current tenant.")
async def list_incident_items(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    return await list_incidents(db, ctx.tenant_id)


@router.post("", response_model=IncidentOut, status_code=201, summary="Create incident", description="Create a new incident for the tenant.")
async def create_incident_endpoint(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    return await create_incident(db, ctx.tenant_id, payload)


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident_endpoint(
    incident_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)
):
    return await get_incident(db, ctx.tenant_id, incident_id)


@router.patch("/{incident_id}", response_model=IncidentOut)
async def update_incident_endpoint(
    incident_id: int,
    payload: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    return await update_incident(db, ctx.tenant_id, incident_id, payload)


@router.delete("/{incident_id}")
async def delete_incident_endpoint(
    incident_id: int, db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)
):
    await delete_incident(db, ctx.tenant_id, incident_id)
    return {"ok": True}
