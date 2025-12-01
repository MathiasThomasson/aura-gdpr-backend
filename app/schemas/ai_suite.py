from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AIDPIAGenerateRequest(BaseModel):
    processing_activity: str
    system_name: str
    risk_factors: List[str] = Field(default_factory=list)
    context: Optional[str] = None
    language: str = Field(default="en", pattern="^[a-z]{2}$")


class AIDPIAGenerateResponse(BaseModel):
    title: str
    purpose: str
    processing_description: str
    data_subjects: str
    data_categories: str
    legal_basis: str
    risks: str
    mitigation_measures: str


class AIIncidentClassifyRequest(BaseModel):
    description: str
    system_name: Optional[str] = None
    data_types: Optional[str] = None
    impact: Optional[str] = None
    context: Optional[str] = None


class AIIncidentClassifyResponse(BaseModel):
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    likely_causes: List[str]
    recommended_actions: List[str]
    regulatory_obligations: str


class AIRopaSuggestRequest(BaseModel):
    system_name: str
    purpose: str
    context: Optional[str] = None
    data_subjects: Optional[str] = None
    data_categories: Optional[str] = None
    recipients: Optional[str] = None
    transfers: Optional[str] = None
    security_measures: Optional[str] = None


class AIRopaSuggestResponse(BaseModel):
    suggested_legal_basis: str
    retention_period: str
    security_measures: str
    risks: str
    notes: str


class AITomsRecommendRequest(BaseModel):
    existing_measures: List[str] = Field(default_factory=list)
    systems: List[str] = Field(default_factory=list)
    risk_profile: Optional[str] = None


class AITomsRecommendItem(BaseModel):
    name: str
    description: str
    category: str
    effectiveness: str


class AITomsRecommendResponse(BaseModel):
    recommended_measures: List[AITomsRecommendItem]


class AIDocumentAutofillRequest(BaseModel):
    document_type: str
    fields: Dict[str, Any]


class AIDocumentAutofillResponse(BaseModel):
    completed_fields: Dict[str, Any]


class AIRiskEvaluateRequest(BaseModel):
    processing_description: str
    data_categories: Optional[str] = None
    data_subjects: Optional[str] = None
    security_measures: Optional[str] = None
    context: Optional[str] = None
    history: List[str] = Field(default_factory=list)
    incidents: List[str] = Field(default_factory=list)
    dpias: List[str] = Field(default_factory=list)
    toms: List[str] = Field(default_factory=list)
    policies: List[str] = Field(default_factory=list)
    language: str = Field(default="en", pattern="^[a-z]{2}$")


class AIRiskEvaluateResponse(BaseModel):
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    overall_risk: str = Field(pattern="^(low|medium|high)$")
    explanation: str
    recommendations: List[str]


class AIAuditV2Request(BaseModel):
    context: Optional[str] = None


class AIAuditArea(BaseModel):
    name: str
    score: int
    summary: str
    recommendations: List[str]


class AIAuditV2Response(BaseModel):
    overall_score: int
    areas: List[AIAuditArea]
    global_recommendations: List[str]


class AIMappingRequest(BaseModel):
    policy: Optional[str] = None
    documents: List[str] = Field(default_factory=list)
    dpia: Optional[str] = None
    ropa: Optional[str] = None
    context: Optional[str] = None


class AIMappingMention(BaseModel):
    module: str
    resource_id: str
    relevance: float
    snippet: str


class AIMappingResponse(BaseModel):
    mentions: List[AIMappingMention]
    gaps: List[str]


class AIExplainRequest(BaseModel):
    text: str


class AIExplainResponse(BaseModel):
    explanation: str


class AISummarizeRequest(BaseModel):
    text: str


class AISummarizeResponse(BaseModel):
    summary: str
