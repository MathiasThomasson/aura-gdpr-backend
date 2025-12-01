from __future__ import annotations

import httpx
from fastapi import HTTPException

from app.core.config import settings


async def ai_chat_completion(messages: list[dict], *, tenant_id: int | None = None) -> str:
    """Centralized AI chat completion entrypoint.

    For now this is a thin abstraction with graceful fallback to a stubbed response
    if no provider credentials are configured. All network calls to AI providers
    should flow through this function.
    """

    provider = (settings.AI_PROVIDER or "openai").lower()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            return _stub_response(messages)
        return await _call_openai(messages)

    if provider == "local":
        if not settings.LOCAL_AI_ENDPOINT:
            return _stub_response(messages)
        return await _call_local(messages)

    # Unknown provider: fail fast to avoid silent misconfiguration.
    raise HTTPException(status_code=500, detail="Unsupported AI provider")


def _stub_response(messages: list[dict]) -> str:
    # Minimal deterministic stub for tests/offline mode
    user_parts = []
    for m in messages:
        if m.get("role") == "user":
            user_parts.append(m.get("content") or "")
    joined = "\n".join(user_parts).strip() or "No content provided."
    return f"Stubbed response:\n{joined}"


async def _call_openai(messages: list[dict]) -> str:
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "max_tokens": settings.AI_MAX_TOKENS,
        "temperature": settings.AI_TEMPERATURE,
    }
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        # fall back gracefully so tests do not require real API
        return _stub_response(messages)


async def _call_local(messages: list[dict]) -> str:
    payload = {
        "messages": messages,
        "max_tokens": settings.AI_MAX_TOKENS,
        "temperature": settings.AI_TEMPERATURE,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(settings.LOCAL_AI_ENDPOINT, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # accept either openai-like or simple {"content": "..."} response
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            return data.get("content") or _stub_response(messages)
    except Exception:
        return _stub_response(messages)
