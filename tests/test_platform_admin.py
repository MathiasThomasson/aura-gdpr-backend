import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.core.config import settings
from main import app

client = TestClient(app)


def _create_tenant(name: str | None = None) -> int:
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (name or f"tenant-{uuid.uuid4().hex[:6]}",))
    tenant_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id


def _create_user(email: str, tenant_id: int) -> int:
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (email, hash_password("pwd"), tenant_id, "owner", "active", 1),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def _auth_headers(user_id: int, tenant_id: int, role: str):
    token = create_access_token({"sub": str(user_id), "tenant_id": tenant_id, "role": role})
    return {"Authorization": f"Bearer {token}"}


def test_platform_admin_can_access_overview():
    tenant_id = _create_tenant()
    admin_id = _create_user(settings.PLATFORM_ADMIN_EMAIL, tenant_id)
    headers = _auth_headers(admin_id, tenant_id, "owner")

    resp = client.get("/api/admin/platform/overview", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "total_tenants" in body and "total_users" in body


def test_non_admin_gets_403():
    tenant_id = _create_tenant()
    user_id = _create_user("someone@example.com", tenant_id)
    headers = _auth_headers(user_id, tenant_id, "owner")

    resp = client.get("/api/admin/platform/overview", headers=headers)
    assert resp.status_code == 403
