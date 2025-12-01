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


def test_ai_answer_returns_sources(monkeypatch):
    tenant_id, user_id = create_user(role="owner")
    override_user(user_id, tenant_id, "owner")

    class Chunk:
        def __init__(self, id, content, section_title=None):
            self.id = id
            self.content = content
            self.section_title = section_title

    async def fake_search(db, tenant_id, query, top_k=5):
        return [
            (0.9, Chunk(1, "This is context about GDPR compliance.", "Policy")),
            (0.5, Chunk(2, "Another snippet"), None),
        ]

    async def fake_chat(messages, tenant_id=None):
        return "Here is your answer based on context."

    monkeypatch.setattr("app.services.rag_service.search", fake_search)
    monkeypatch.setattr("app.services.ai_client.ai_chat_completion", fake_chat)

    resp = client.post("/api/ai/answer", json={"question": "What is GDPR?"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["answer"]
    assert len(data["sources"]) == 2
    assert data["sources"][0]["title"]


def test_ai_answer_requires_auth():
    resp = client.post("/api/ai/answer", json={"question": "Hello"})
    assert resp.status_code in (401, 403)
