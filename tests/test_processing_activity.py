from fastapi.testclient import TestClient
from main import app

import sqlite3
from app.core.auth import get_current_user


client = TestClient(app)


def test_processing_activity_crud_flow():
    # Create tenant row directly in sqlite dev.db
    import uuid
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"test-tenant-{uuid.uuid4().hex[:8]}"
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

    # Create processing activity (no Authorization header required because dependency overridden)
    create_payload = {"name": "PA One", "description": "First processing activity"}
    r = client.post("/api/processing_activities/", json=create_payload)
    assert r.status_code == 200, r.text
    pa = r.json()
    pa_id = pa["id"]
    assert pa["name"] == "PA One"

    # List
    r = client.get("/api/processing_activities/")
    assert r.status_code == 200
    items = r.json()
    assert any(i["id"] == pa_id for i in items)

    # Get
    r = client.get(f"/api/processing_activities/{pa_id}")
    assert r.status_code == 200
    got = r.json()
    assert got["id"] == pa_id

    # Update
    r = client.put(f"/api/processing_activities/{pa_id}", json={"name": "PA Updated"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["name"] == "PA Updated"

    # Delete
    r = client.delete(f"/api/processing_activities/{pa_id}")
    assert r.status_code == 200
    r = client.get(f"/api/processing_activities/{pa_id}")
    assert r.status_code == 404
