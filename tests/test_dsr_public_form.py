import sqlite3
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app

client = TestClient(app)


def create_tenant_and_user(role="owner"):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
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


def override_user(user_id, tenant_id, role):
    class Dummy:
        def __init__(self, uid, tid, r):
            self.id = uid
            self.tenant_id = tid
            self.role = r
            self.email = "dummy@example.com"

    app.dependency_overrides[get_current_user] = lambda: Dummy(user_id, tenant_id, role)


def test_can_enable_disable_public_link():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")

    initial = client.get("/api/dsr/public-link")
    assert initial.status_code == 200
    assert initial.json()["enabled"] is False

    enabled = client.post("/api/dsr/public-link/enable")
    assert enabled.status_code == 200
    enabled_data = enabled.json()
    assert enabled_data["enabled"] is True
    assert enabled_data["public_url"]
    public_key = enabled_data["public_url"].rstrip("/").split("/")[-1]

    disabled = client.post("/api/dsr/public-link/disable")
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert disabled.json()["public_url"] is None

    reenabled = client.post("/api/dsr/public-link/enable")
    assert reenabled.status_code == 200
    assert reenabled.json()["public_url"].endswith(public_key)


def test_public_submission_creates_dsr_and_deadline():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")
    enabled = client.post("/api/dsr/public-link/enable")
    public_key = enabled.json()["public_url"].rstrip("/").split("/")[-1]

    payload = {
        "request_type": "Access Request",
        "subject_name": "Alice Example",
        "subject_email": "alice@example.com",
        "description": "Please share my data.",
        "priority": "High",
    }
    before = datetime.utcnow()
    resp = client.post(f"/api/public/dsr/{public_key}", json=payload)
    after = datetime.utcnow()
    assert resp.status_code == 201
    resp_data = resp.json()
    assert resp_data["status"] == "received"

    deadline = datetime.fromisoformat(resp_data["deadline"])
    expected_min = before + timedelta(days=30)
    expected_max = after + timedelta(days=30, seconds=2)
    assert expected_min <= deadline <= expected_max

    override_user(user_id, tenant_id, "owner")
    dsrs = client.get("/api/dsr/").json()
    assert len(dsrs) == 1
    dsr = dsrs[0]
    assert dsr["tenant_id"] == tenant_id
    assert dsr["source"] == "public_form"
    assert dsr["priority"] == "high"
    assert dsr["subject_name"] == payload["subject_name"]


def test_public_submission_invalid_or_disabled_key():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")
    enabled = client.post("/api/dsr/public-link/enable")
    public_key = enabled.json()["public_url"].rstrip("/").split("/")[-1]
    disable_resp = client.post("/api/dsr/public-link/disable")
    assert disable_resp.status_code == 200

    payload = {
        "request_type": "Deletion",
        "subject_name": "Bob Example",
        "subject_email": "bob@example.com",
        "description": "Delete me",
        "priority": "Low",
    }
    resp_disabled = client.post(f"/api/public/dsr/{public_key}", json=payload)
    assert resp_disabled.status_code == 404

    resp_invalid = client.post("/api/public/dsr/doesnotexist", json=payload)
    assert resp_invalid.status_code == 404
