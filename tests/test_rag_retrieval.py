import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app


client = TestClient(app)


def _prep_tenant_user():
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"rag-{uuid.uuid4().hex[:6]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
    tid = cur.lastrowid
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)",
        (f"{name}@example.com", hash_password("pwd"), tid, "owner"),
    )
    uid = cur.lastrowid
    conn.commit()
    conn.close()
    return tid, uid


def _override_user(tid, uid):
    class Dummy:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "owner"

    app.dependency_overrides[get_current_user] = lambda: Dummy(uid, tid)


def test_rag_isolation_and_retrieval_scoring():
    t1, u1 = _prep_tenant_user()
    _override_user(t1, u1)
    # create doc for tenant1
    client.post("/api/rag/documents", json={"content": "# Title\nTenant one content about apples", "title": "A"})
    r = client.post("/api/rag/search", json={"query": "apples"})
    assert r.status_code == 200
    data = r.json()
    assert data["citations"]
    scores = [c["score"] for c in data["citations"]]
    assert all(s >= 0 for s in scores)

    # tenant2 should not see tenant1 chunks
    t2, u2 = _prep_tenant_user()
    _override_user(t2, u2)
    r2 = client.post("/api/rag/search", json={"query": "apples"})
    assert r2.status_code == 200
    assert r2.json().get("citations") == []

    app.dependency_overrides.clear()
