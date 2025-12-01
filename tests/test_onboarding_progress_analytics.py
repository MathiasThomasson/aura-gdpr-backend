import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from main import app

client = TestClient(app)


def create_tenant_and_user(role="user", tenant_id=None):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    if tenant_id is None:
        name = f"tenant-{uuid.uuid4().hex[:6]}"
        cur.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
        tenant_id = cur.lastrowid
    email = f"{uuid.uuid4().hex[:6]}@example.com"
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (email, hash_password("pwd"), tenant_id, role, "active", 1),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id, user_id, email


def auth_headers(user_id: int, tenant_id: int, role: str = "user"):
    token = create_access_token({"sub": str(user_id), "tenant_id": tenant_id, "role": role})
    return {"Authorization": f"Bearer {token}"}


def test_onboarding_state_flow():
    tenant_id, user_id, _ = create_tenant_and_user()
    headers = auth_headers(user_id, tenant_id)

    resp = client.get("/api/onboarding/state", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["onboarding_step"] == 0

    resp = client.patch("/api/onboarding/state", json={"onboarding_step": 2, "onboarding_completed": True}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["onboarding_step"] == 2
    assert data["onboarding_completed"] is True


def test_user_progress_patch_and_get():
    tenant_id, user_id, _ = create_tenant_and_user()
    headers = auth_headers(user_id, tenant_id)

    resp = client.get("/api/user-progress", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["created_first_dsr"] is False

    resp = client.patch("/api/user-progress", json={"created_first_dsr": True, "ran_ai_audit": True}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created_first_dsr"] is True
    assert data["ran_ai_audit"] is True


def test_analytics_event_created():
    tenant_id, user_id, _ = create_tenant_and_user()
    headers = auth_headers(user_id, tenant_id)
    resp = client.post("/api/analytics/event", json={"event_name": "clicked_button"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["event_name"] == "clicked_button"
    assert resp.json()["tenant_id"] == tenant_id
    assert resp.json()["user_id"] == user_id


def test_demo_tenant_blocks_writes():
    tenant_id, user_id, _ = create_tenant_and_user()
    headers = auth_headers(user_id, tenant_id)
    # Temporarily set demo tenant ID
    original_demo = settings.DEMO_TENANT_ID
    settings.DEMO_TENANT_ID = tenant_id
    resp = client.post("/api/analytics/event", json={"event_name": "blocked"}, headers=headers)
    settings.DEMO_TENANT_ID = original_demo
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Demo tenant is read-only."


def test_version_endpoint():
    resp = client.get("/api/system/version")
    assert resp.status_code == 200
    body = resp.json()
    assert "version" in body
    assert "build" in body
