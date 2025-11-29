from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import CurrentContext, current_context

router = APIRouter(prefix="/api/risk", tags=["Risk"])


class RiskCell(BaseModel):
    label: Optional[str] = None
    likelihood: Optional[str] = None
    impact: Optional[str] = None
    score: Optional[float] = None


class RiskMatrixResponse(BaseModel):
    matrix: List[List[RiskCell]] = Field(default_factory=list)
    risks: List[RiskCell] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=lambda: {"high": 0, "medium": 0, "low": 0})


@router.get("/", response_model=RiskMatrixResponse)
async def get_risk_matrix(ctx: CurrentContext = Depends(current_context)):
    return RiskMatrixResponse()
