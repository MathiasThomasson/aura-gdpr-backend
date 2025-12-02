import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from main import app

client = TestClient(app)


def _create_user_with_membership(role: str = "owner", *, tenant_id: int | None = None, is_active: bool = True):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_tenants (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            role VARCHAR NOT NULL DEFAULT 'member',
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(user_id, tenant_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS ix_user_tenants_user_id ON user_tenants (user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_user_tenants_tenant_id ON user_tenants (tenant_id)")
    if tenant_id is None:
        cur.execute("INSERT INTO tenants (name) VALUES (?)", (f"tenant-{uuid.uuid4().hex[:6]}",))
        tenant_id = cur.lastrowid
    email = f"{uuid.uuid4().hex[:6]}@example.com"
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (
            email,
            hash_password("pwd"),
            tenant_id,
            role,
            "active" if is_active else "disabled",
            1 if is_active else 0,
        ),
    )
    user_id = cur.lastrowid
    cur.execute(
        "INSERT INTO user_tenants (user_id, tenant_id, role, is_active) VALUES (?, ?, ?, ?)",
        (user_id, tenant_id, role, 1 if is_active else 0),
    )
    user_tenant_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id, user_id, user_tenant_id, email


def _auth_headers(user_id: int, tenant_id: int, role: str):
    token = create_access_token({"sub": str(user_id), "tenant_id": tenant_id, "role": role})
    return {"Authorization": f"Bearer {token}"}


def test_owner_can_list_only_their_tenant_users():
    tenant_id, owner_id, _, _ = _create_user_with_membership("owner")
    # another user in same tenant
    _, other_user_id, _, _ = _create_user_with_membership("viewer", tenant_id=tenant_id)
    # user in different tenant should not appear
    other_tenant_id, outsider_user_id, _, _ = _create_user_with_membership("user")

    headers = _auth_headers(owner_id, tenant_id, "owner")
    resp = client.get("/api/admin/workspace/users", headers=headers)
    assert resp.status_code == 200
    ids = {u["id"] for u in resp.json()}
    assert owner_id in ids
    assert other_user_id in ids
    assert outsider_user_id not in ids
    # verify tenant id matches
    assert all(u["tenant_id"] == tenant_id for u in resp.json())
    assert other_tenant_id != tenant_id


def test_non_admin_cannot_access_workspace_iam():
    tenant_id, user_id, _, _ = _create_user_with_membership("user")
    headers = _auth_headers(user_id, tenant_id, "user")
    resp = client.get("/api/admin/workspace/users", headers=headers)
    assert resp.status_code == 403


def test_invite_creates_user_tenant_membership():
    tenant_id, owner_id, _, _ = _create_user_with_membership("owner")
    headers = _auth_headers(owner_id, tenant_id, "owner")
    invite_email = f"{uuid.uuid4().hex[:6]}@example.com"

    resp = client.post(
        "/api/admin/workspace/users/invite",
        json={"email": invite_email, "role": "viewer"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == invite_email
    assert body["role"] == "viewer"
    assert body["status"] == "active"
    assert body["tenant_id"] == tenant_id

    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM user_tenants ut JOIN users u ON ut.user_id = u.id WHERE u.email = ? AND ut.tenant_id = ?",
        (invite_email, tenant_id),
    )
    count = cur.fetchone()[0]
    conn.close()
    assert count == 1


def test_patch_updates_role_and_status():
    tenant_id, owner_id, _, _ = _create_user_with_membership("owner")
    _, target_user_id, target_ut_id, _ = _create_user_with_membership("user", tenant_id=tenant_id)
    headers = _auth_headers(owner_id, tenant_id, "owner")

    resp = client.patch(
        f"/api/admin/workspace/users/{target_ut_id}",
        json={"role": "admin", "status": "disabled"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
    assert body["status"] == "disabled"
    assert body["id"] == target_user_id

    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute("SELECT role, is_active FROM user_tenants WHERE id = ?", (target_ut_id,))
    role, is_active = cur.fetchone()
    conn.close()
    assert role == "admin"
    assert is_active == 0


def test_cannot_demote_last_owner():
    tenant_id, owner_id, owner_ut_id, _ = _create_user_with_membership("owner")
    headers = _auth_headers(owner_id, tenant_id, "owner")

    resp = client.patch(
        f"/api/admin/workspace/users/{owner_ut_id}",
        json={"role": "admin"},
        headers=headers,
    )
    assert resp.status_code == 400
