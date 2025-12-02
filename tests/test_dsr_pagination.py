import sqlite3
import uuid

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


def test_dsr_list_pagination():
    tenant_id, user_id, email = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")
    for i in range(5):
        payload = {
            "request_type": f"type-{i}",
            "subject_name": f"subject-{i}",
            "subject_email": email,
            "status": "open",
        }
        resp = client.post("/api/dsr/", json=payload)
        assert resp.status_code == 201
    resp = client.get("/api/dsr/?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    resp2 = client.get("/api/dsr/?limit=2&offset=2")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2
