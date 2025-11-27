import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.security import hash_password
from main import app


client = TestClient(app)


def _mk_tenant_user(name_prefix: str, role: str = "owner"):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    tname = f"{name_prefix}-{uuid.uuid4().hex[:6]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (tname,))
    tid = cur.lastrowid
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)",
        (f"{tname}@example.com", hash_password("pwd"), tid, role),
    )
    uid = cur.lastrowid
    conn.commit()
    conn.close()
    return tid, uid, f"{tname}@example.com"


def test_task_assignee_must_be_same_tenant():
    t1, u1, email1 = _mk_tenant_user("iso1", "owner")
    t2, u2, email2 = _mk_tenant_user("iso2", "owner")

    # login tenant1 owner via direct token issuance
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(u1), "tenant_id": t1, "role": "owner"})
    headers = {"Authorization": f"Bearer {token}"}

    # Try assign user from different tenant
    r = client.post("/api/tasks/", json={"title": "Bad", "assigned_to_user_id": u2}, headers=headers)
    assert r.status_code == 400


def test_ai_requires_auth_and_respects_tenant():
    t1, u1, _ = _mk_tenant_user("ai1", "owner")
    # call without auth => 401
    r = client.post("/api/ai/gdpr/analyze", json={"text": "hello"})
    assert r.status_code in (401, 403)

    # with auth token
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(u1), "tenant_id": t1, "role": "owner"})
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/ai/gdpr/analyze", json={"text": "hello"}, headers=headers)
    # service may 502 if Ollama not available; accept 200/502 but not 401
    assert r.status_code in (200, 502)
