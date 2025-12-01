import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app

client = TestClient(app)


def create_tenant_user(role="owner"):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (f"tenant-{uuid.uuid4().hex[:6]}",))
    tenant_id = cur.lastrowid
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (f"{uuid.uuid4().hex[:6]}@example.com", hash_password("pwd"), tenant_id, role, "active", 1),
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


def test_audit_run_creation_and_latest():
    tenant_id, user_id = create_tenant_user(role="owner")
    override_user(user_id, tenant_id, "owner")

    resp = client.post("/api/ai/audit/run")
    assert resp.status_code == 201
    created = resp.json()

    latest = client.get("/api/ai/audit/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == created["id"]


def test_audit_history_ordering():
    tenant_id, user_id = create_tenant_user(role="admin")
    override_user(user_id, tenant_id, "admin")

    first = client.post("/api/ai/audit/run").json()
    second = client.post("/api/ai/audit/run").json()

    history = client.get("/api/ai/audit/history")
    assert history.status_code == 200
    data = history.json()
    assert data["total"] >= 2
    assert data["items"][0]["id"] == second["id"]
    assert first["id"] in [item["id"] for item in data["items"]]


def test_audit_tenant_isolation():
    tenant1, user1 = create_tenant_user(role="owner")
    tenant2, user2 = create_tenant_user(role="owner")

    override_user(user2, tenant2, "owner")
    client.post("/api/ai/audit/run")

    override_user(user1, tenant1, "owner")
    latest = client.get("/api/ai/audit/latest")
    assert latest.status_code == 404
    history = client.get("/api/ai/audit/history")
    assert history.status_code == 200
    assert history.json()["total"] == 0
