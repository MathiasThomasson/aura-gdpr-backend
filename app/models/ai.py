from pydantic import BaseModel, Field
from typing import List

class GDPRAnalyzeRequest(BaseModel):
    # Limit input text to 50,000 characters to avoid large model prompts
    text: str = Field(..., max_length=50000)

class GDPRAnalyzeResponse(BaseModel):
    summary: str
    risks: List[str]
    recommendations: List[str]
    high_risk: bool
    model: str

    model_config = {"from_attributes": True}
