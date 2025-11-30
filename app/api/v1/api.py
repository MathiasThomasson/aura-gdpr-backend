from fastapi import APIRouter

from app.api.v1.endpoints import risk_matrix

router = APIRouter()

router.include_router(risk_matrix.router)
