import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app

client = TestClient(app)


def create_user(role="owner"):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (f"tenant-{uuid.uuid4().hex[:6]}",))
    tenant_id = cur.lastrowid
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (f"{uuid.uuid4().hex[:6]}@example.com", "pw", tenant_id, role, "active", 1),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id, user_id


def override_user(user_id, tenant_id, role):
    class Dummy:
        def __init__(self, uid, tid, r):
            self.id = uid
            self.tenant_id = tid
            self.role = r
            self.email = "dummy@example.com"

    app.dependency_overrides[get_current_user] = lambda: Dummy(user_id, tenant_id, role)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_generate_policy_returns_content(monkeypatch):
    tenant_id, user_id = create_user(role="admin")
    override_user(user_id, tenant_id, "admin")

    async def fake_chat(messages, tenant_id=None):
        return "Privacy Policy\nThis is a short summary. More details. Thank you.\nFull content section."

    monkeypatch.setattr("app.services.ai_client.ai_chat_completion", fake_chat)

    resp = client.post(
        "/api/ai/policies/generate",
        json={"policy_type": "privacy_policy", "context_description": "Test org", "language": "en"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["content"]
    assert "summary" in body


def test_generate_policy_requires_auth():
    resp = client.post("/api/ai/policies/generate", json={"policy_type": "privacy_policy", "language": "en"})
    assert resp.status_code in (401, 403)
