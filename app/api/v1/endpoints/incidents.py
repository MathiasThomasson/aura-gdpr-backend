from fastapi import APIRouter

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("")
async def list_incidents():
    return {"items": []}
