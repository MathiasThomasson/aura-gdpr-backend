import os
import pytest
from fastapi.testclient import TestClient
import sqlite3
import json
from app.core.security import hash_password
from main import app

client = TestClient(app)


@pytest.mark.skipif(not os.environ.get("OLLAMA_BASE_URL"), reason="OLLAMA not configured")
def test_ai_integration_and_audit_log():
    # require OLLAMA reachable
    base = os.environ.get("OLLAMA_BASE_URL")
    import requests
    try:
        r = requests.get(f"{base}/api/tags", timeout=2)
        if r.status_code != 200:
            pytest.skip("Ollama not available: /api/tags returned non-200")
    except Exception:
        pytest.skip("Ollama not available")

    # setup tenant & user in test DB
    conn = sqlite3.connect("dev.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", ("test-ollama-tenant",))
    tenant_id = cur.lastrowid
    hashed = hash_password("pwd")
    cur.execute("INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)", ("aiuser@example.com", hashed, tenant_id, "owner"))
    user_id = cur.lastrowid
    conn.commit()

    headers = {
        "X-Tenant-Id": str(tenant_id),
        "X-User-Id": str(user_id),
    }

    payload = {"text": "Detta är en testtext för AI integration som beskriver behandling av personuppgifter."}
    r = client.post("/api/ai/gdpr/analyze", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert all(k in data for k in ("summary", "risks", "recommendations", "high_risk", "model"))

    # Verify audit_log contains a record for this tenant and action
    cur.execute("SELECT id, tenant_id, user_id, entity_type, action, meta FROM audit_logs WHERE tenant_id = ? ORDER BY id DESC LIMIT 1", (tenant_id,))
    row = cur.fetchone()
    assert row is not None
    assert row[3] == 'ai_call'
    assert row[4] == 'analyze_gdpr_text'
    meta = json.loads(row[5]) if row[5] else {}
    assert meta.get('status') == 'success'
    assert meta.get('model') == os.environ.get('AI_MODEL', 'llama3.2:1b')

    conn.close()
