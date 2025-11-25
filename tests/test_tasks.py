from fastapi.testclient import TestClient
from main import app
import sqlite3
from app.core.auth import get_current_user

client = TestClient(app)


def test_task_crud_flow():
    # prepare tenant and override user
    import uuid
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"task-tenant-{uuid.uuid4().hex[:8]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
    tenant_id = cur.lastrowid
    conn.commit()
    conn.close()

    class DummyUser:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "owner"

    dummy = DummyUser(1, tenant_id)
    app.dependency_overrides[get_current_user] = lambda: dummy

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
