import asyncio
import pytest
import os
from app.services.ai_service import analyze_gdpr_text


class DummyResp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status


@pytest.mark.asyncio
async def test_analyze_gdpr_text_fallback(monkeypatch):
    sample_text = "SUMMARY: Sammanfattning\nRISKS:\n- Risk A\nRECOMMENDATIONS:\n- Gör B\nHIGH_RISK:\nNO"

    async def fake_post(self, url, json=None):
        return DummyResp(sample_text, 200)

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    res = await analyze_gdpr_text("Det här är en testtext")
    assert isinstance(res, dict)
    assert res["summary"].startswith("Sammanfattning")
    assert res["risks"] == ["Risk A"]
    assert res["recommendations"] == ["Gör B"]
    assert res["high_risk"] is False
    assert res["model"]
