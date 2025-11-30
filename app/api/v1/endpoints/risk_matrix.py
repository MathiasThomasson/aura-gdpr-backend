from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentContext, current_context

router = APIRouter(prefix="/api/risk-matrix", tags=["Risk Matrix"])


class RiskMatrixItem(BaseModel):
    id: int
    title: str
    severity: str
    likelihood: str
    score: float


class RiskMatrixResponse(BaseModel):
    items: List[RiskMatrixItem] = Field(default_factory=list)


@router.get("/", response_model=RiskMatrixResponse)
async def get_risk_matrix(ctx: CurrentContext = Depends(current_context)):
    return RiskMatrixResponse()
