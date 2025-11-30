import json
import pytest

from app.services import ai_service


class _DummyResponse:
    def __init__(self, body: dict):
        self.status_code = 200
        self.text = json.dumps(body)

    def json(self):
        return json.loads(self.text)


@pytest.mark.asyncio
async def test_analyze_uses_ollama_provider(monkeypatch):
    # reset circuit state
    ai_service._cb_failure_count = 0
    ai_service._cb_open_since = None

    captured = {}
    monkeypatch.setattr(ai_service.settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(ai_service.settings, "AI_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setattr(ai_service.settings, "AI_MODEL", "gemma:2b")
    monkeypatch.setattr(ai_service.settings, "AI_RETRY_ATTEMPTS", 0)

    async def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _DummyResponse(
            {
                "summary": "ok",
                "risks": ["r1"],
                "recommendations": ["rec1"],
                "high_risk": False,
                "model": "gemma:2b",
            }
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    result = await ai_service.analyze_gdpr_text("Hello world")

    assert captured["url"] == "http://127.0.0.1:11434/api/generate"
    assert captured["json"]["model"] == "gemma:2b"
    assert captured["json"]["stream"] is False
    assert captured["headers"] is None
    assert result["model"] == "gemma:2b"
    assert result["summary"] == "ok"
