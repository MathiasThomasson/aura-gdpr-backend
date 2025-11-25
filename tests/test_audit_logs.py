from fastapi.testclient import TestClient
from main import app
import sqlite3
from app.core.auth import get_current_user

client = TestClient(app)


def test_audit_logs_recorded_for_actions():
    # create tenant and override current_user
    import uuid
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"audit-tenant-{uuid.uuid4().hex[:8]}"
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

    # Create a processing activity (should create audit log)
    r = client.post("/api/processing_activities/", json={"name": "A1"})
    assert r.status_code == 200

    # Create a task
    r = client.post("/api/tasks/", json={"title": "T1"})
    assert r.status_code == 200

    # List audit logs
    r = client.get("/api/audit_logs/")
    assert r.status_code == 200
    items = r.json()
    # expect at least two audit events
    assert len(items) >= 2
