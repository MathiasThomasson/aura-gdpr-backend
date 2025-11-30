import json
import os
import re
import time
import asyncio
from collections import deque
import logging
from typing import Dict, List

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.models.ai import GDPRAnalyzeResponse

logger = logging.getLogger(__name__)

# Circuit breaker state (in-memory)
_cb_failure_count: int = 0
_cb_open_since: float | None = None
_cb_last_failure_ts: float | None = None
_cb_lock: asyncio.Lock = asyncio.Lock()
_cb_history_max = int(settings.AI_CB_HISTORY_MAX or 50)
_cb_failure_history: deque = deque(maxlen=_cb_history_max)


def _provider() -> str:
    return (settings.AI_PROVIDER or "ollama").lower()


def _base_url(provider: str) -> str:
    if provider == "ollama":
        base = os.environ.get("OLLAMA_BASE_URL") or settings.AI_BASE_URL or settings.OLLAMA_BASE_URL or "http://127.0.0.1:11434"
    else:
        base = settings.AI_BASE_URL or "https://api.openai.com"
    return base.rstrip("/")


def _build_request(provider: str, prompt: str, base_url: str):
    model = _model()
    if provider == "ollama":
        url = f"{base_url}/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False}
        headers = None
    else:
        api_base = base_url
        if not api_base.endswith("/v1"):
            api_base = f"{api_base}/v1"
        url = f"{api_base}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if settings.AI_API_KEY:
            headers["Authorization"] = f"Bearer {settings.AI_API_KEY}"
    return url, payload, headers


def _extract_text(provider: str, response: httpx.Response) -> str:
    if provider == "ollama":
        return response.text
    try:
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", response.text)
    except Exception:
        return response.text


def _model() -> str:
    return settings.AI_MODEL


async def get_circuit_breaker_status() -> Dict:
    async with _cb_lock:
        failure_count = _cb_failure_count
        open_since = _cb_open_since
        last_failure_ts = _cb_last_failure_ts
    threshold = int(settings.AI_CB_FAILURE_THRESHOLD or 5)
    cooldown = int(settings.AI_CB_COOLDOWN_SECONDS or 30)
    now = time.time()
    if open_since is not None:
        remaining = int(max(0, cooldown - (now - open_since)))
        state = "open"
    else:
        remaining = 0
        state = "closed"
    return {
        "state": state,
        "failure_count": int(failure_count),
        "cooldown_seconds_remaining": remaining,
        "last_failure_timestamp": (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(last_failure_ts)) if last_failure_ts else None),
        "threshold": threshold,
        "cooldown": cooldown,
    }


async def get_circuit_breaker_history() -> List[Dict]:
    async with _cb_lock:
        return list(_cb_failure_history)


async def reset_circuit_breaker() -> None:
    global _cb_failure_count, _cb_open_since, _cb_last_failure_ts
    async with _cb_lock:
        _cb_failure_count = 0
        _cb_open_since = None
        _cb_last_failure_ts = None
        _cb_failure_history.clear()


async def analyze_gdpr_text(text: str) -> Dict:
    max_chars = int(settings.AI_MAX_INPUT_CHARS or 50000)
    trimmed_text = text[:max_chars]
    prompt = (
        "Du ar en expertradgivare (DPO) som hjalper till med GDPR-analys. "
        "Las foljande text och gor foljande och returnera ENDAST giltig JSON med foljande format: \n\n"
        f"TEXT:\n{trimmed_text}\n\n"
        "Uppdrag:\n"
        "1) Returnera JSON-objekt med foljande nycklar: summary (string), risks (lista av strangar), recommendations (lista av strangar), high_risk (boolean), model (string).\n"
        "2) JSON ska vara strikt giltig (dubbelcitat, inga kommentarer, inga textutskrifter utanfor JSON).\n"
        "3) Svar ska inte innehalla nagot annat an JSON.\n\n"
    )

    provider = _provider()
    base_url = _base_url(provider)
    url, payload, headers = _build_request(provider, prompt, base_url)
    max_retries = int(settings.AI_RETRY_ATTEMPTS or 2)
    backoff = float(settings.AI_RETRY_BACKOFF_SECONDS or 0.5)
    resp = None
    latency = 0.0
    global _cb_failure_count, _cb_open_since, _cb_last_failure_ts
    cb_threshold = int(settings.AI_CB_FAILURE_THRESHOLD or 5)
    cb_cooldown = int(settings.AI_CB_COOLDOWN_SECONDS or 30)
    now = time.time()
    if _cb_open_since is not None and now - _cb_open_since < cb_cooldown:
        logger.warning("AI circuit is OPEN; rejecting call")
        raise HTTPException(status_code=503, detail="AI circuit is open; service temporarily unavailable")

    async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
        for attempt in range(max_retries + 1):
            try:
                start = time.perf_counter()
                resp = await client.post(url, json=payload, headers=headers or None)
                latency = time.perf_counter() - start
                break
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    await asyncio.sleep(backoff * (attempt + 1))
                    continue
                async with _cb_lock:
                    _cb_failure_count += 1
                    _cb_last_failure_ts = time.time()
                    if _cb_failure_count >= cb_threshold:
                        _cb_open_since = time.time()
                    _cb_failure_history.append({"timestamp": int(_cb_last_failure_ts), "error": str(exc)[:256]})
                raise HTTPException(status_code=502, detail=f"Could not reach {provider} at {base_url}: {exc}")

    if resp.status_code != 200:
        async with _cb_lock:
            _cb_failure_count += 1
            _cb_last_failure_ts = time.time()
            if _cb_failure_count >= cb_threshold:
                _cb_open_since = time.time()
            _cb_failure_history.append({"timestamp": int(_cb_last_failure_ts), "error": f"status={resp.status_code} text={str(resp.text)[:256]}"})
        raise HTTPException(status_code=502, detail=f"{provider} returned status {resp.status_code}: {resp.text}")

    text_out = _extract_text(provider, resp)
    parsed = None
    try:
        parsed = json.loads(text_out)
    except Exception:
        try:
            m = re.search(r"\{(?:.|\n)*\}", text_out)
            if m:
                parsed = json.loads(m.group(0))
        except Exception:
            parsed = None

    if parsed is None:
        try:
            fixed = text_out.replace("'", '"')
            fixed = re.sub(r",\s*([\]}])", r"\1", fixed)
            parsed = json.loads(fixed)
        except Exception:
            parsed = None

    def _strip_prefix(prefix: str, s: str) -> str:
        if s.lower().startswith(prefix.lower()):
            return s[len(prefix):].strip()
        return s.strip()

    summary = ""
    risks: List[str] = []
    recommendations: List[str] = []
    high_risk = False

    current_section = None
    for raw in text_out.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("SUMMARY:"):
            current_section = "summary"
            summary = _strip_prefix("SUMMARY:", line)
            continue
        if line.upper().startswith("RISKS:"):
            current_section = "risks"
            continue
        if line.upper().startswith("RECOMMENDATIONS:"):
            current_section = "recommendations"
            continue
        if line.upper().startswith("HIGH_RISK:"):
            current_section = "high_risk"
            val = _strip_prefix("HIGH_RISK:", line).lower()
            high_risk = val.startswith("y") or val in ("ja", "yes", "true")
            continue

        if current_section == "summary":
            summary = (summary + " " + line).strip() if summary else line
        elif current_section == "risks":
            cleaned = line.lstrip("-*").strip()
            risks.append(cleaned)
        elif current_section == "recommendations":
            cleaned = line.lstrip("-*").strip()
            recommendations.append(cleaned)
        elif current_section == "high_risk":
            v = line.lower()
            high_risk = v.startswith("y") or v in ("ja", "yes", "true")
        else:
            if line.lower().startswith("summary:"):
                current_section = "summary"
                summary = _strip_prefix("summary:", line)
            elif line.lower().startswith("risks:"):
                current_section = "risks"
            elif line.lower().startswith("recommendations:"):
                current_section = "recommendations"
            elif line.lower().startswith("high_risk:"):
                current_section = "high_risk"
                v = _strip_prefix("high_risk:", line).lower()
                high_risk = v.startswith("y") or v in ("ja", "yes", "true")

    if not summary:
        summary = text_out.strip().splitlines()[0][:200]
    if parsed is not None and isinstance(parsed, dict):
        try:
            GDPRAnalyzeResponse.model_validate(parsed)
        except ValidationError as ve:
            logger.warning("Parsed JSON did not validate against GDPRAnalyzeResponse model: %s", ve)
            parsed = None
        except Exception as ve:
            logger.warning("Error validating parsed JSON: %s", ve)
            parsed = None
        try:
            summary = parsed.get("summary", summary)
            risks = parsed.get("risks", risks)
            recommendations = parsed.get("recommendations", recommendations)
            high_risk = parsed.get("high_risk", parsed.get("HIGH_RISK", high_risk))
        except Exception:
            pass

    if not isinstance(risks, list):
        risks = [str(risks)] if risks else []
    if not isinstance(recommendations, list):
        recommendations = [str(recommendations)] if recommendations else []

    max_output = int(settings.AI_MAX_OUTPUT_CHARS or 20000)
    summary = summary[:max_output]
    risks = [r[:1024] for r in risks][:50]
    recommendations = [r[:1024] for r in recommendations][:50]

    result = {
        "summary": summary,
        "risks": [r for r in risks if r],
        "recommendations": [r for r in recommendations if r],
        "high_risk": bool(high_risk),
        "model": _model(),
    }

    async with _cb_lock:
        _cb_failure_count = 0
        _cb_open_since = None
        _cb_last_failure_ts = None
    logger.info("AI analyze result: model=%s latency=%.3f summary_len=%d risks=%d recs=%d high_risk=%s", _model(), latency, len(result["summary"]), len(result["risks"]), len(result["recommendations"]), result["high_risk"])
    return result
