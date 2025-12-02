from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.incident import Incident
from app.schemas.incidents import IncidentCreate, IncidentUpdate
from app.services.simple_crud_service import SimpleCRUDService

service = SimpleCRUDService[Incident](Incident)


async def list_incidents(db: AsyncSession, tenant_id: int):
    return await service.list(db, tenant_id)


async def create_incident(db: AsyncSession, tenant_id: int, payload: IncidentCreate):
    data = payload.model_dump(exclude_unset=True)
    data.setdefault("severity", "low")
    data.setdefault("status", "open")
    return await service.create(db, tenant_id, data)


async def get_incident(db: AsyncSession, tenant_id: int, incident_id: int):
    return await service.get_or_404(db, tenant_id, incident_id)


async def update_incident(db: AsyncSession, tenant_id: int, incident_id: int, payload: IncidentUpdate):
    incident = await service.get_or_404(db, tenant_id, incident_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return incident
    # ensure updated_at reflects manual changes when DB defaults aren't triggered
    data.setdefault("updated_at", datetime.utcnow())
    return await service.update(db, incident, data)


async def delete_incident(db: AsyncSession, tenant_id: int, incident_id: int):
    incident = await service.get_or_404(db, tenant_id, incident_id)
    await service.delete(db, incident)
    return {"ok": True}
