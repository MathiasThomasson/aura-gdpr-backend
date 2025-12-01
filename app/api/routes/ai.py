from fastapi import APIRouter, Depends, HTTPException, Request
import asyncio
import time
import logging
import httpx
import os
from typing import Any
from pydantic import ValidationError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_audit import log_ai_call
from app.core.config import settings
from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.middleware.rate_limit import rate_limit
from app.models.ai import GDPRAnalyzeRequest, GDPRAnalyzeResponse
from app.services.ai_service import (
    analyze_gdpr_text,
    get_circuit_breaker_status,
    get_circuit_breaker_history,
    reset_circuit_breaker,
)
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
)
from app.services.ai_suite_service import (
    autofill_document,
    classify_incident,
    evaluate_risk,
    explain_text,
    generate_dpia,
    map_modules,
    recommend_toms,
    run_audit_v2,
    summarize_text,
    suggest_ropa,
)

router = APIRouter(prefix="/api/ai", tags=["AI"])

logger = logging.getLogger(__name__)

# Simple in-memory rate limit store: {ip: last_request_timestamp}
_rate_limit_lock = asyncio.Lock()
_rate_limit_state: dict[str, list[float]] = {}
_RATE_LIMIT_TTL = int(settings.AI_RATE_LIMIT_TTL_SECONDS or 300)


@router.post("/gdpr/analyze", response_model=GDPRAnalyzeResponse, summary="AI GDPR analyze", description="Analyze GDPR posture of provided text.")
@rate_limit("ai", limit=20, window_seconds=60)
async def analyze_gdpr(
    req: GDPRAnalyzeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    # simple per-IP rate limit: 1 request per second
    ip = request.client.host if request.client else request.headers.get("x-forwarded-for", "unknown")
    now = time.time()
    async with _rate_limit_lock:
        # cleanup old entries to avoid memory growth
        if len(_rate_limit_state) > 0:
            cutoff = now - _RATE_LIMIT_TTL
            keys_to_remove = [k for k, v in _rate_limit_state.items() if not any(ts >= cutoff for ts in v)]
            for k in keys_to_remove:
                del _rate_limit_state[k]
        values = _rate_limit_state.get(ip, [])
        # remove timestamps older than window
        # read runtime-configurable window + max requests
        _RATE_LIMIT_WINDOW = int(settings.AI_RATE_LIMIT_WINDOW_SECONDS or 60)
        _RATE_LIMIT_MAX_REQUESTS = int(settings.AI_RATE_LIMIT_MAX_REQUESTS or 30)
        window_cutoff = now - _RATE_LIMIT_WINDOW
        values = [ts for ts in values if ts >= window_cutoff]
        if len(values) >= _RATE_LIMIT_MAX_REQUESTS:
            logger.warning("Rate limit exceeded for IP %s (count=%d window=%ds max=%d)", ip, len(values), _RATE_LIMIT_WINDOW, _RATE_LIMIT_MAX_REQUESTS)
            raise HTTPException(status_code=429, detail="Too many requests; please retry later")
        values.append(now)
        _rate_limit_state[ip] = values

    # Validate input length (defensive); GDPRAnalyzeRequest includes a pydantic max_length, but return 400 instead of 422
    if req.text is None or len(req.text) == 0:
        raise HTTPException(status_code=400, detail="Missing or empty text field")
    max_chars = int(settings.AI_MAX_INPUT_CHARS or 50000)
    if len(req.text) > max_chars:
        raise HTTPException(status_code=400, detail=f"Text exceeds maximum length of {max_chars} characters")

    tenant_id = ctx.tenant_id
    user_id = ctx.user.id
    logger.info("AI analyze requested: ip=%s tenant=%s user=%s model=%s input_size=%d", ip, tenant_id, user_id, settings.AI_MODEL, len(req.text))
    # Perform analysis by delegating to the service layer
    try:
        result = await analyze_gdpr_text(req.text)
    except HTTPException as e:
        logger.error("AI analyze failed for ip=%s: %s", ip, e.detail)
        # audit error
        try:
            await log_ai_call(db, tenant_id, user_id, req.text, settings.AI_MODEL, "/api/ai/gdpr/analyze", False, "error", str(e.detail))
        except Exception:
            logger.exception("Failed to write AI error audit log")
        raise e
    except Exception as e:
        logger.exception("Unexpected AI analyze error for ip=%s: %s", ip, e)
        try:
            await log_ai_call(db, tenant_id, user_id, req.text, settings.AI_MODEL, "/api/ai/gdpr/analyze", False, "error", str(e))
        except Exception:
            logger.exception("Failed to write AI error audit log")
        raise HTTPException(status_code=500, detail="Internal error during AI analysis")

    # Validate result using Pydantic and then write audit log if possible
    try:
        response_obj = GDPRAnalyzeResponse.model_validate(result)
    except ValidationError as ve:
        logger.error("AI result validation failed: %s", ve)
        # attempt audit log of error if tenant_id provided
        try:
            await log_ai_call(db, tenant_id, user_id, req.text, settings.AI_MODEL, "/api/ai/gdpr/analyze", False, "error", str(ve))
        except Exception:
            logger.exception("Failed to write AI error audit log")
        raise HTTPException(status_code=502, detail="AI returned invalid structured response")

    # Write successful audit log if tenant_id provided
    try:
        await log_ai_call(db, tenant_id, user_id, req.text, settings.AI_MODEL, "/api/ai/gdpr/analyze", response_obj.high_risk, "success")
    except Exception:
        logger.exception("Failed to write AI success audit log")

    return response_obj


@router.get("/health", summary="AI provider health", description="Health check for configured AI provider.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ollama_health(request: Request):
    """Return Ollama basic health (tags/models)."""
    provider = (settings.AI_PROVIDER or "ollama").lower()
    base = (os.environ.get("OLLAMA_BASE_URL") or settings.AI_BASE_URL or settings.OLLAMA_BASE_URL or "http://127.0.0.1:11434").rstrip("/")
    if provider != "ollama":
        return {"status": "ok", "provider": provider, "detail": "health check available only for Ollama provider"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/api/tags")
        if resp.status_code == 200:
            models = resp.json()
            return {"status": "ok", "models": models}
        else:
            return {"status": "unhealthy", "code": resp.status_code, "detail": resp.text}
    except Exception as e:
        logger.exception("Ollama health check failed: %s", e)
        return {"status": "unhealthy", "detail": str(e)}


@router.get("/circuit", summary="AI circuit status", description="Return circuit breaker status for AI calls.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_circuit_status(request: Request):
    """Return circuit breaker status for AI/Ollama calls."""
    status = await get_circuit_breaker_status()
    return status


@router.get("/circuit/history", summary="AI circuit history", description="Return recent circuit breaker failures.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_circuit_history(request: Request):
    """Return the last failures captured by circuit breaker (read-only)."""
    history = await get_circuit_breaker_history()
    return {"history": history}


@router.post("/circuit/reset", summary="Reset AI circuit", description="Reset AI circuit breaker (admin/owner only).")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_circuit_reset(request: Request, ctx: CurrentContext = Depends(current_context)):
    """Reset the circuit breaker state (clear failure history and counters). Admin only."""
    from app.core.roles import Role

    if ctx.role not in (Role.ADMIN.value, Role.OWNER.value):
        raise HTTPException(status_code=403, detail="Forbidden")
    await reset_circuit_breaker()
    return {"status": "ok"}


# === GDPR AI Suite ===


@router.post("/dpia/generate", response_model=AIDPIAGenerateResponse, tags=["AI"], summary="Generate DPIA", description="Generate a DPIA draft using AI.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_generate_dpia(
    payload: AIDPIAGenerateRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await generate_dpia(ctx.tenant_id, payload)


@router.post("/incidents/classify", response_model=AIIncidentClassifyResponse, tags=["AI"], summary="Classify incident", description="Classify an incident using AI.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_incident_classify(
    payload: AIIncidentClassifyRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await classify_incident(ctx.tenant_id, payload)


@router.post("/ropa/suggest", response_model=AIRopaSuggestResponse, tags=["AI"], summary="Suggest ROPA", description="Suggest ROPA entries with AI assistance.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_ropa_suggest(
    payload: AIRopaSuggestRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await suggest_ropa(ctx.tenant_id, payload)


@router.post("/toms/recommend", response_model=AITomsRecommendResponse, tags=["AI"], summary="Recommend TOMs", description="Recommend technical and organisational measures.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_toms_recommend(
    payload: AITomsRecommendRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await recommend_toms(ctx.tenant_id, payload)


@router.post("/autofill", response_model=AIDocumentAutofillResponse, tags=["AI"], summary="Autofill document", description="Autofill document data using AI.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_autofill_document(
    payload: AIDocumentAutofillRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await autofill_document(ctx.tenant_id, payload)


@router.post("/risk/evaluate", response_model=AIRiskEvaluateResponse, tags=["AI"], summary="Evaluate risk", description="Evaluate risk using AI.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_risk_evaluate(
    payload: AIRiskEvaluateRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await evaluate_risk(ctx.tenant_id, payload)


@router.post("/audit/run-v2", response_model=AIAuditV2Response, tags=["AI"], summary="Run AI audit", description="Execute AI-based audit v2.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_audit_run_v2(
    payload: AIAuditV2Request,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    return await run_audit_v2(db, ctx.tenant_id, payload)


@router.post("/mapping", response_model=AIMappingResponse, tags=["AI"], summary="Map modules", description="Map modules to GDPR controls using AI.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_mapping(
    payload: AIMappingRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await map_modules(ctx.tenant_id, payload)


@router.post("/explain", response_model=AIExplainResponse, tags=["AI"], summary="Explain text", description="Explain provided text with AI assistance.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_explain(
    payload: AIExplainRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await explain_text(ctx.tenant_id, payload)


@router.post("/summarize", response_model=AISummarizeResponse, tags=["AI"], summary="Summarize text", description="Summarize text using AI.")
@rate_limit("ai", limit=20, window_seconds=60)
async def ai_summarize(
    payload: AISummarizeRequest,
    request: Request,
    ctx: CurrentContext = Depends(current_context),
):
    return await summarize_text(ctx.tenant_id, payload)
