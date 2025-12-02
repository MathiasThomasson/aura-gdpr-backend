import sqlite3
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app

client = TestClient(app)


def create_tenant_and_user(role: str = "owner"):
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


def override_user(user_id: int, tenant_id: int, role: str):
    class Dummy:
        def __init__(self, uid, tid, r):
            self.id = uid
            self.tenant_id = tid
            self.role = r
            self.email = "dummy@example.com"

    app.dependency_overrides[get_current_user] = lambda: Dummy(user_id, tenant_id, role)


def test_dsr_defaults_status_and_deadline():
    tenant_id, user_id, email = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")

    before = datetime.utcnow()
    resp = client.post(
        "/api/dsr/",
        json={
            "request_type": "Access Request",
            "subject_name": "Alice",
            "subject_email": email,
            "description": "Check my data",
        },
    )
    after = datetime.utcnow()

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "received"
    assert data["is_overdue"] is False

    created_at = datetime.fromisoformat(data["created_at"])
    deadline = datetime.fromisoformat(data["deadline"])
    assert before - timedelta(seconds=5) <= created_at <= after + timedelta(seconds=5)
    assert abs((deadline - created_at) - timedelta(days=30)) < timedelta(seconds=2)


def test_change_status_creates_history_and_rejects_invalid():
    tenant_id, user_id, email = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")

    resp = client.post(
        "/api/dsr/",
        json={
            "request_type": "Deletion",
            "subject_name": "Bob",
            "subject_email": email,
        },
    )
    assert resp.status_code == 201
    dsr_id = resp.json()["id"]

    change = client.patch(f"/api/dsr/{dsr_id}/status", json={"status": "in_progress", "note": "Reviewing"})
    assert change.status_code == 200
    assert change.json()["status"] == "in_progress"

    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute(
        "SELECT from_status, to_status, changed_by_user_id, note FROM dsr_status_history WHERE dsr_id=?", (dsr_id,)
    )
    history_rows = cur.fetchall()
    conn.close()

    assert len(history_rows) == 1
    from_status, to_status, changed_by, note = history_rows[0]
    assert from_status == "received"
    assert to_status == "in_progress"
    assert changed_by == user_id
    assert note == "Reviewing"

    invalid = client.patch(f"/api/dsr/{dsr_id}/status", json={"status": "not_a_status"})
    assert invalid.status_code == 400


def test_list_filters_by_status():
    tenant_id, user_id, email = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")

    first = client.post("/api/dsr/", json={"request_type": "Access", "subject_name": "One", "subject_email": email})
    second = client.post("/api/dsr/", json={"request_type": "Access", "subject_name": "Two", "subject_email": email})
    assert first.status_code == 201 and second.status_code == 201
    first_id = first.json()["id"]
    second_id = second.json()["id"]

    client.patch(f"/api/dsr/{first_id}/status", json={"status": "in_progress"})
    client.patch(f"/api/dsr/{second_id}/status", json={"status": "identity_verification"})

    resp_single = client.get("/api/dsr/?status=in_progress&limit=10")
    assert resp_single.status_code == 200
    ids_single = {item["id"] for item in resp_single.json()}
    assert ids_single == {first_id}

    resp_multi = client.get("/api/dsr/?status=in_progress&status=identity_verification&limit=10")
    assert resp_multi.status_code == 200
    ids_multi = {item["id"] for item in resp_multi.json()}
    assert ids_multi.issuperset({first_id, second_id})


def test_overdue_filter_and_is_overdue_boundary():
    tenant_id, user_id, email = create_tenant_and_user()
    override_user(user_id, tenant_id, "owner")

    overdue_deadline = datetime.utcnow() - timedelta(days=1)
    today_deadline = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    future_deadline = datetime.utcnow() + timedelta(days=5)

    overdue = client.post("/api/dsr/", json={"request_type": "Access", "subject_name": "Over", "subject_email": email})
    today = client.post("/api/dsr/", json={"request_type": "Access", "subject_name": "Today", "subject_email": email})
    completed = client.post(
        "/api/dsr/", json={"request_type": "Access", "subject_name": "Done", "subject_email": email}
    )

    overdue_id = overdue.json()["id"]
    today_id = today.json()["id"]
    completed_id = completed.json()["id"]

    client.patch(f"/api/dsr/{overdue_id}", json={"deadline": overdue_deadline.isoformat()})
    client.patch(f"/api/dsr/{today_id}", json={"deadline": today_deadline.isoformat()})
    client.patch(f"/api/dsr/{completed_id}", json={"deadline": future_deadline.isoformat()})
    client.patch(f"/api/dsr/{completed_id}/status", json={"status": "completed"})

    overdue_resp = client.get("/api/dsr/?overdue=true&limit=20")
    assert overdue_resp.status_code == 200
    overdue_ids = {item["id"] for item in overdue_resp.json()}
    assert overdue_id in overdue_ids
    assert today_id not in overdue_ids
    assert completed_id not in overdue_ids
    assert all(item["status"] != "completed" for item in overdue_resp.json())

    all_dsrs = client.get("/api/dsr/?limit=20").json()
    flags = {item["id"]: item["is_overdue"] for item in all_dsrs}
    assert flags[overdue_id] is True
    assert flags[today_id] is False
    assert flags[completed_id] is False
