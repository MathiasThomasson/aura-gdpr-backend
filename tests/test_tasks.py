import sqlite3
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app

client = TestClient(app)


def _prep_tenant():
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"task-tenant-{uuid.uuid4().hex[:8]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
    tenant_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id


def _override_user(tenant_id: int, user_id: int = 1):
    class DummyUser:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "owner"

    dummy = DummyUser(user_id, tenant_id)
    app.dependency_overrides[get_current_user] = lambda: dummy


def test_task_crud_flow():
    tenant_id = _prep_tenant()
    _override_user(tenant_id)

    # Create task
    payload = {"title": "Task 1", "description": "Do something", "status": "open"}
    r = client.post("/api/tasks/", json=payload)
    assert r.status_code == 200, r.text
    t = r.json()
    task_id = t["id"]

    # List
    r = client.get("/api/tasks/")
    assert r.status_code == 200
    items = r.json()
    assert any(i["id"] == task_id for i in items)

    # Get
    r = client.get(f"/api/tasks/{task_id}")
    assert r.status_code == 200

    # Update
    r = client.put(f"/api/tasks/{task_id}", json={"title": "Task Updated"})
    assert r.status_code == 200
    assert r.json()["title"] == "Task Updated"

    # Delete
    r = client.delete(f"/api/tasks/{task_id}")
    assert r.status_code == 200
    r = client.get(f"/api/tasks/{task_id}")
    assert r.status_code == 404
    app.dependency_overrides.clear()


def test_task_filters_and_status_validation():
    tenant_id = _prep_tenant()
    _override_user(tenant_id)

    # create tasks with different statuses and due dates
    now = datetime.utcnow()
    t1 = client.post("/api/tasks/", json={"title": "A", "status": "open", "due_date": now.isoformat()}).json()
    t2 = client.post("/api/tasks/", json={"title": "B", "status": "completed", "due_date": (now + timedelta(days=1)).isoformat()}).json()

    # filter by status
    r = client.get("/api/tasks/", params={"status": "completed"})
    assert r.status_code == 200
    items = r.json()
    assert all(i["status"] == "completed" for i in items)

    # invalid status filter
    r = client.get("/api/tasks/", params={"status": "not_valid"})
    assert r.status_code == 400
    app.dependency_overrides.clear()
