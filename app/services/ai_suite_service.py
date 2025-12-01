import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_run import AuditRun
from app.db.models.document import Document
from app.db.models.dsr import DataSubjectRequest
from app.db.models.task import Task
from app.schemas.ai_suite import (
    AIAuditV2Request,
    AIAuditV2Response,
    AIDocumentAutofillRequest,
    AIDocumentAutofillResponse,
    AIDPIAGenerateRequest,
    AIDPIAGenerateResponse,
    AIExplainRequest,
    AIExplainResponse,
    AIMappingRequest,
    AIMappingResponse,
    AIIncidentClassifyRequest,
    AIIncidentClassifyResponse,
    AIRiskEvaluateRequest,
    AIRiskEvaluateResponse,
    AIRopaSuggestRequest,
    AIRopaSuggestResponse,
    AISummarizeRequest,
    AISummarizeResponse,
    AITomsRecommendRequest,
    AITomsRecommendResponse,
    AITomsRecommendItem,
)
from app.services.ai_client import ai_chat_completion


def _safe_json_parse(text: str, fallback: dict) -> dict:
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    return fallback


async def generate_dpia(tenant_id: int, payload: AIDPIAGenerateRequest) -> AIDPIAGenerateResponse:
    system_prompt = (
        "You are an expert GDPR privacy consultant. Generate a concise DPIA summary in English. "
        "Return JSON with keys: title, purpose, processing_description, data_subjects, data_categories, "
        "legal_basis, risks, mitigation_measures."
    )
    user_prompt = (
        f"Processing activity: {payload.processing_activity}\n"
        f"System name: {payload.system_name}\n"
        f"Risk factors: {', '.join(payload.risk_factors) if payload.risk_factors else 'None provided'}\n"
        f"Context: {payload.context or 'Not provided'}\n"
        "Language: English\n"
        "Return short, actionable statements."
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback = {
        "title": f"DPIA for {payload.system_name}",
        "purpose": payload.processing_activity,
        "processing_description": payload.processing_activity,
        "data_subjects": "Data subjects not specified.",
        "data_categories": "Data categories not specified.",
        "legal_basis": "Legitimate interest (validate).",
        "risks": "Risks were not detailed; perform deeper assessment.",
        "mitigation_measures": "Implement access control, encryption, and review data minimization.",
    }
    data = _safe_json_parse(raw, fallback)
    return AIDPIAGenerateResponse(**{**fallback, **data})


async def classify_incident(tenant_id: int, payload: AIIncidentClassifyRequest) -> AIIncidentClassifyResponse:
    system_prompt = (
        "You are a security incident handler. Classify severity and propose actions in English. "
        "Respond as JSON with: severity (low|medium|high|critical), likely_causes (list), "
        "recommended_actions (list), regulatory_obligations."
    )
    user_prompt = (
        f"Description: {payload.description}\n"
        f"System: {payload.system_name or 'Unknown'}\n"
        f"Data types: {payload.data_types or 'Not specified'}\n"
        f"Impact: {payload.impact or 'Not specified'}\n"
        f"Context: {payload.context or 'Not provided'}"
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback = {
        "severity": "medium",
        "likely_causes": ["Misconfiguration or user error"],
        "recommended_actions": ["Contain the incident", "Notify stakeholders", "Investigate root cause"],
        "regulatory_obligations": "Assess if personal data was impacted and notify DPA/individuals if required.",
    }
    data = _safe_json_parse(raw, fallback)
    return AIIncidentClassifyResponse(**{**fallback, **data})


async def suggest_ropa(tenant_id: int, payload: AIRopaSuggestRequest) -> AIRopaSuggestResponse:
    system_prompt = (
        "You assist with Records of Processing Activities (ROPA). "
        "Provide concise English suggestions. Return JSON with suggested_legal_basis, "
        "retention_period, security_measures, risks, notes."
    )
    user_prompt = (
        f"System: {payload.system_name}\nPurpose: {payload.purpose}\n"
        f"Context: {payload.context or 'Not provided'}\n"
        f"Data subjects: {payload.data_subjects or 'Unknown'}\n"
        f"Data categories: {payload.data_categories or 'Unknown'}\n"
        f"Recipients: {payload.recipients or 'Unknown'}\n"
        f"Transfers: {payload.transfers or 'Unknown'}\n"
        f"Security measures: {payload.security_measures or 'Unknown'}"
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback = {
        "suggested_legal_basis": "Legitimate interests (confirm with DPO).",
        "retention_period": "12-24 months based on business need.",
        "security_measures": payload.security_measures or "Apply encryption, access control, backups.",
        "risks": "Potential over-retention and unauthorized access.",
        "notes": "Validate DPIA requirements and update ROPA once finalized.",
    }
    data = _safe_json_parse(raw, fallback)
    return AIRopaSuggestResponse(**{**fallback, **data})


async def recommend_toms(tenant_id: int, payload: AITomsRecommendRequest) -> AITomsRecommendResponse:
    system_prompt = (
        "You recommend technical and organizational measures (TOMs) for GDPR security. "
        "Return JSON with key 'recommended_measures' as a list of objects with name, description, category, effectiveness."
    )
    user_prompt = (
        f"Existing measures: {', '.join(payload.existing_measures) if payload.existing_measures else 'None'}\n"
        f"Systems: {', '.join(payload.systems) if payload.systems else 'Unknown'}\n"
        f"Risk profile: {payload.risk_profile or 'Not provided'}"
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback_items = [
        {"name": "Access Control", "description": "Role-based access with MFA.", "category": "identity", "effectiveness": "high"},
        {"name": "Encryption", "description": "Encrypt data at rest and in transit.", "category": "encryption", "effectiveness": "high"},
    ]
    parsed = _safe_json_parse(raw, {"recommended_measures": fallback_items})
    measures_raw = parsed.get("recommended_measures") or fallback_items
    measures: List[AITomsRecommendItem] = []
    for item in measures_raw:
        if isinstance(item, dict):
            merged = {**fallback_items[0], **item}
            measures.append(AITomsRecommendItem(**merged))
    if not measures:
        measures = [AITomsRecommendItem(**m) for m in fallback_items]
    return AITomsRecommendResponse(recommended_measures=measures)


async def autofill_document(tenant_id: int, payload: AIDocumentAutofillRequest) -> AIDocumentAutofillResponse:
    system_prompt = (
        "You are an AI assisting with GDPR document authoring. "
        "Complete missing fields in English. Return JSON with 'completed_fields' containing key/value pairs."
    )
    user_prompt = (
        f"Document type: {payload.document_type}\n"
        f"Fields: {json.dumps(payload.fields, ensure_ascii=False)}"
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback = {"completed_fields": payload.fields}
    parsed = _safe_json_parse(raw, fallback)
    completed = parsed.get("completed_fields") or payload.fields
    if not isinstance(completed, dict):
        completed = payload.fields
    return AIDocumentAutofillResponse(completed_fields=completed)


async def evaluate_risk(tenant_id: int, payload: AIRiskEvaluateRequest) -> AIRiskEvaluateResponse:
    system_prompt = (
        "You evaluate GDPR risks. Provide likelihood (1-5), impact (1-5), overall_risk (low|medium|high), "
        "explanation, and recommendations (list). Respond in JSON."
    )
    user_prompt = (
        f"Processing: {payload.processing_description}\n"
        f"Data categories: {payload.data_categories or 'Unknown'}\n"
        f"Data subjects: {payload.data_subjects or 'Unknown'}\n"
        f"Security measures: {payload.security_measures or 'Unknown'}\n"
        f"Context: {payload.context or 'None'}\n"
        f"History: {payload.history}\nIncidents: {payload.incidents}\nDPIAs: {payload.dpias}\n"
        f"TOMs: {payload.toms}\nPolicies: {payload.policies}\nLanguage: English"
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback = {
        "likelihood": 3,
        "impact": 3,
        "overall_risk": "medium",
        "explanation": "Risk could not be fully determined; more data needed.",
        "recommendations": ["Add encryption", "Review access control", "Perform DPIA"],
    }
    parsed = _safe_json_parse(raw, fallback)
    return AIRiskEvaluateResponse(**{**fallback, **parsed})


async def _count(db: AsyncSession, model, tenant_id: int) -> int:
    try:
        stmt = select(func.count()).select_from(model)
        if hasattr(model, "tenant_id"):
            stmt = stmt.where(model.tenant_id == tenant_id)
        res = await db.execute(stmt)
        return res.scalar_one()
    except Exception:
        return 0


async def run_audit_v2(db: AsyncSession, tenant_id: int, payload: AIAuditV2Request) -> AIAuditV2Response:
    docs = await _count(db, Document, tenant_id)
    dsrs = await _count(db, DataSubjectRequest, tenant_id)
    tasks = await _count(db, Task, tenant_id)
    context_summary = (
        f"Docs: {docs}, DSRs: {dsrs}, Tasks: {tasks}. "
        f"Extra context: {payload.context or 'None provided.'}"
    )
    system_prompt = (
        "You are an auditor producing a GDPR compliance assessment. "
        "Return JSON with keys: overall_score (0-100), areas (list of objects: name, score, summary, recommendations[list]), "
        "global_recommendations (list). Keep it concise and in English."
    )
    user_prompt = (
        "Assess tenant data across chapters: Lawfulness, Records of processing, Rights of data subjects, "
        "Processor management, Security measures, DPIA, Incident handling. "
        f"Data snapshot: {context_summary}"
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback = {
        "overall_score": 60,
        "areas": [
            {"name": "Lawfulness", "score": 60, "summary": "Basic controls present.", "recommendations": ["Document legal basis"]},
            {"name": "Security measures", "score": 55, "summary": "Improvements needed on access control.", "recommendations": ["Enable MFA"]},
        ],
        "global_recommendations": ["Prioritize DPIA for high-risk systems", "Refresh incident response playbooks"],
    }
    parsed = _safe_json_parse(raw, fallback)
    merged = {**fallback, **parsed}
    # Persist audit run
    audit_run = AuditRun(
        tenant_id=tenant_id,
        overall_score=int(merged.get("overall_score", 60) or 60),
        raw_result=merged,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(audit_run)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
    return AIAuditV2Response(**merged)


async def map_modules(tenant_id: int, payload: AIMappingRequest) -> AIMappingResponse:
    system_prompt = (
        "You cross-reference GDPR artifacts. Identify mentions and gaps. "
        "Return JSON with 'mentions' (list of {module, resource_id, relevance, snippet}) and 'gaps' (list of strings). "
        "English only."
    )
    user_prompt = (
        f"Policy: {payload.policy or 'None'}\n"
        f"Documents: {payload.documents}\n"
        f"DPIA: {payload.dpia or 'None'}\n"
        f"ROPA: {payload.ropa or 'None'}\n"
        f"Context: {payload.context or 'None'}"
    )
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        tenant_id=tenant_id,
    )
    fallback = {
        "mentions": [],
        "gaps": ["No cross-module references detected; align DPIA and ROPA entries."],
    }
    parsed = _safe_json_parse(raw, fallback)
    mentions_raw = parsed.get("mentions") or []
    mentions = []
    for item in mentions_raw:
        if isinstance(item, dict):
            try:
                mentions.append(
                    {
                        "module": item.get("module", "Unknown"),
                        "resource_id": item.get("resource_id", "n/a"),
                        "relevance": float(item.get("relevance", 0.5)),
                        "snippet": item.get("snippet", "No snippet provided."),
                    }
                )
            except Exception:
                continue
    return AIMappingResponse(mentions=mentions, gaps=parsed.get("gaps") or fallback["gaps"])


async def explain_text(tenant_id: int, payload: AIExplainRequest) -> AIExplainResponse:
    system_prompt = "Explain GDPR content in plain English. Return JSON with key 'explanation'."
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": payload.text}],
        tenant_id=tenant_id,
    )
    parsed = _safe_json_parse(raw, {"explanation": raw})
    return AIExplainResponse(**{"explanation": parsed.get("explanation", raw)})


async def summarize_text(tenant_id: int, payload: AISummarizeRequest) -> AISummarizeResponse:
    system_prompt = "Summarize the provided text in concise English. Return JSON with key 'summary'."
    raw = await ai_chat_completion(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": payload.text}],
        tenant_id=tenant_id,
    )
    parsed = _safe_json_parse(raw, {"summary": raw})
    return AISummarizeResponse(**{"summary": parsed.get("summary", raw)})
