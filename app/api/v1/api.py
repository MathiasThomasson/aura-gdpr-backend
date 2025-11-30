from fastapi import APIRouter

from app.api.v1.endpoints import incidents, risk_matrix

router = APIRouter()

router.include_router(risk_matrix.router)
router.include_router(incidents.router, prefix="/api", tags=["incidents"])
