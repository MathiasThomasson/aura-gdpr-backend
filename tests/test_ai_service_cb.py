import asyncio
import pytest
import httpx
import time
from app.services import ai_service
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_rejects_calls(monkeypatch):
    # reset circuit breaker state
    ai_service._cb_failure_count = 0
    ai_service._cb_open_since = None

    async def fake_post_raise(self, url, json=None):
        raise httpx.RequestError("Connection failed")

    # monkeypatch httpx AsyncClient.post to raise
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post_raise)
    # reduce retries for faster test
    monkeypatch.setattr(ai_service.settings, "AI_RETRY_ATTEMPTS", 0)

    # perform calls up to threshold
    threshold = int(ai_service.settings.AI_CB_FAILURE_THRESHOLD)
    for i in range(threshold):
        with pytest.raises(HTTPException):
            await ai_service.analyze_gdpr_text("test")

    # now circuit should be open; a new call should be rejected quickly with 503
    with pytest.raises(HTTPException) as e:
        await ai_service.analyze_gdpr_text("test")
    assert e.value.status_code == 503

    # cleanup
    ai_service._cb_failure_count = 0
    ai_service._cb_open_since = None