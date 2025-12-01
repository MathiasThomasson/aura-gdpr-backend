import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app

client = TestClient(app)


def create_tenant_user(role="user", tenant_id=None, email=None, status="active"):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    if tenant_id is None:
        cur.execute("INSERT INTO tenants (name) VALUES (?)", (f"tenant-{uuid.uuid4().hex[:6]}",))
        tenant_id = cur.lastrowid
    email = email or f"{uuid.uuid4().hex[:6]}@example.com"
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (email, hash_password("pwd"), tenant_id, role, status, 1 if status == "active" else 0),
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


def test_regular_user_cannot_manage_iam():
    tenant_id, user_id = create_tenant_user(role="user")
    override_user(user_id, tenant_id, "user")
    resp = client.get("/api/iam/users")
    assert resp.status_code == 403


def test_invite_creates_pending_user():
    tenant_id, owner_id = create_tenant_user(role="owner")
    override_user(owner_id, tenant_id, "owner")
    payload = {"name": "Invited", "email": "invite@example.com", "role": "viewer"}

    resp = client.post("/api/iam/users/invite", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending_invite"

    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute("SELECT status FROM users WHERE email = ?", (payload["email"],))
    row = cur.fetchone()
    conn.close()
    assert row[0] == "pending_invite"


def test_status_changes_work():
    tenant_id, owner_id = create_tenant_user(role="owner")
    _, target_id = create_tenant_user(role="user", tenant_id=tenant_id)
    override_user(owner_id, tenant_id, "owner")

    disable_resp = client.patch(f"/api/iam/users/{target_id}", json={"status": "disabled"})
    assert disable_resp.status_code == 200
    assert disable_resp.json()["status"] == "disabled"

    activate_resp = client.patch(f"/api/iam/users/{target_id}", json={"status": "active"})
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "active"


def test_tenant_isolation_on_get_user():
    tenant1, owner1 = create_tenant_user(role="owner")
    tenant2, other_user = create_tenant_user(role="user")
    override_user(owner1, tenant1, "owner")

    resp = client.get(f"/api/iam/users/{other_user}")
    assert resp.status_code == 404
