from fastapi import APIRouter

from app.api.v1.endpoints import incidents, platform_admin, risk_matrix, workspace_iam

router = APIRouter()

router.include_router(risk_matrix.router)
router.include_router(incidents.router, prefix="/api", tags=["incidents"])
router.include_router(workspace_iam.router)
router.include_router(platform_admin.router)
