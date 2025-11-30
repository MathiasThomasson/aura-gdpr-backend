from fastapi.testclient import TestClient
from main import app
import pytest
import os

client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_ai_service(monkeypatch):
    # monkeypatch the analyze_gdpr_text service to avoid calling the real Ollama instance in tests
    async def fake_analyze(text: str):
        return {
            "summary": "Kort sammanfattning",
            "risks": ["Risk 1", "Risk 2"],
            "recommendations": ["Åtgärd 1", "Åtgärd 2"],
            "high_risk": False,
            "model": os.environ.get("AI_MODEL", "gemma:2b"),
        }

    # Patch the function in the router module, because the router imported the symbol at import time
    monkeypatch.setattr("app.api.routes.ai.analyze_gdpr_text", fake_analyze)
    yield


def test_ai_endpoint_returns_expected_structure():
    payload = {"text": "Detta är en testtext som kan innehålla GDPR-relevant information."}
    r = client.post("/api/ai/gdpr/analyze", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "risks" in data and isinstance(data["risks"], list)
    assert "recommendations" in data and isinstance(data["recommendations"], list)
    assert "high_risk" in data and isinstance(data["high_risk"], bool)
    assert "model" in data
