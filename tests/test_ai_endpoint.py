import os
import pytest
import json
from fastapi.testclient import TestClient
from main import app
import time

client = TestClient(app)


_ollama_url = os.environ.get("AI_BASE_URL") or os.environ.get("OLLAMA_BASE_URL")


@pytest.mark.skipif(not _ollama_url, reason="OLLAMA not available")
def test_ollama_health_real():
    r = client.get("/api/ai/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


def test_analyze_rate_limit_and_input(monkeypatch):
    # monkeypatch analyze_gdpr_text to avoid real model and to speed up
    async def fake_analyze(text: str):
        return {
            "summary": "Kort",
            "risks": ["R1"],
            "recommendations": ["A1"],
            "high_risk": False,
            "model": os.environ.get("AI_MODEL", "gemma:2b"),
        }

    monkeypatch.setattr("app.api.routes.ai.analyze_gdpr_text", fake_analyze)

    # clear rate limit store to avoid test-pollution from other tests
    try:
        import app.api.routes.ai as ai_module
        ai_module._rate_limit_state.clear()
    except Exception:
        pass

    # Set limit low for test to validate single-request limit
    from app.core.config import settings as cfg
    monkeypatch.setattr(cfg, "AI_RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(cfg, "AI_RATE_LIMIT_WINDOW_SECONDS", 60)
    payload = {"text": "Test text"}
    r1 = client.post("/api/ai/gdpr/analyze", json=payload)
    assert r1.status_code == 200

    # second immediate request should be rate-limited (same IP)
    r2 = client.post("/api/ai/gdpr/analyze", json=payload)
    assert r2.status_code == 429

    # oversize input test: ensure rate-limiter doesn't interfere
    try:
        ai_module._rate_limit_state.clear()
    except Exception:
        pass
    # oversize input test
    long_text = "x" * 50001
    r3 = client.post("/api/ai/gdpr/analyze", json={"text": long_text})
    assert r3.status_code == 400


def test_analyze_writes_audit_log(monkeypatch):
    # ensure DB has a tenant and user
    import sqlite3
    from app.core.security import hash_password

    conn = sqlite3.connect("dev.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", ("audit-tenant",))
    tenant_id = cur.lastrowid
    h = hash_password("pwd")
    cur.execute("INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)", ("audituser@example.com", h, tenant_id, "owner"))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()


def test_ai_audit_input_privacy(monkeypatch):
    # ensure DB has a tenant and user
    import sqlite3
    from app.core.security import hash_password
    from app.core.config import settings as cfg
    import json as _json

    conn = sqlite3.connect("dev.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", ("audit-tenant-privacy",))
    tenant_id = cur.lastrowid
    h = hash_password("pwd")
    cur.execute("INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)", ("audituser2@example.com", h, tenant_id, "owner"))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    async def fake_analyze(text: str):
        return {
            "summary": "Kort",
            "risks": ["R1"],
            "recommendations": ["A1"],
            "high_risk": True,
            "model": os.environ.get("AI_MODEL", "gemma:2b"),
        }

    monkeypatch.setattr("app.api.routes.ai.analyze_gdpr_text", fake_analyze)
    try:
        import app.api.routes.ai as ai_module
        ai_module._rate_limit_state.clear()
    except Exception:
        pass

    headers = {"X-Tenant-Id": str(tenant_id), "X-User-Id": str(user_id)}
    long_text = "x" * 600

    # Default: AI_AUDIT_STORE_INPUT is False
    monkeypatch.setattr(cfg, "AI_AUDIT_STORE_INPUT", False)
    r = client.post("/api/ai/gdpr/analyze", json={"text": long_text}, headers=headers)
    assert r.status_code == 200
    conn = sqlite3.connect("dev.db")
    cur = conn.cursor()
    cur.execute("SELECT metadata FROM audit_logs WHERE tenant_id = ? ORDER BY id DESC LIMIT 1", (tenant_id,))
    row = cur.fetchone()
    assert row is not None
    meta = _json.loads(row[0])
    assert 'input_hash_sha256' in meta
    assert 'input_text' not in meta
    conn.close()

    # Now enable storing input text but with a small max length
    monkeypatch.setattr(cfg, "AI_AUDIT_STORE_INPUT", True)
    monkeypatch.setattr(cfg, "AI_AUDIT_INPUT_MAX_LENGTH", 10)
    try:
        ai_module._rate_limit_state.clear()
    except Exception:
        pass
    r = client.post("/api/ai/gdpr/analyze", json={"text": long_text}, headers=headers)
    assert r.status_code == 200
    conn = sqlite3.connect("dev.db")
    cur = conn.cursor()
    cur.execute("SELECT metadata FROM audit_logs WHERE tenant_id = ? ORDER BY id DESC LIMIT 1", (tenant_id,))
    row = cur.fetchone()
    assert row is not None
    meta = _json.loads(row[0])
    assert 'input_text' in meta
    assert len(meta['input_text']) <= 10
    conn.close()

    async def fake_analyze(text: str):
        return {
            "summary": "Kort",
            "risks": ["R1"],
            "recommendations": ["A1"],
            "high_risk": True,
            "model": os.environ.get("AI_MODEL", "gemma:2b"),
        }

    monkeypatch.setattr("app.api.routes.ai.analyze_gdpr_text", fake_analyze)
    # clear rate limiter
    try:
        import app.api.routes.ai as ai_module
        ai_module._rate_limit_state.clear()
    except Exception:
        pass

    headers = {"X-Tenant-Id": str(tenant_id), "X-User-Id": str(user_id)}
    r = client.post("/api/ai/gdpr/analyze", json={"text": "test"}, headers=headers)
    assert r.status_code == 200

    # check audit log
    conn = sqlite3.connect("dev.db")
    cur = conn.cursor()
    cur.execute("SELECT metadata FROM audit_logs WHERE tenant_id = ? ORDER BY id DESC LIMIT 1", (tenant_id,))
    row = cur.fetchone()
    assert row is not None
    meta = json.loads(row[0])
    assert meta.get("status") == "success"
    assert meta.get("high_risk") is True
    conn.close()
