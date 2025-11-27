import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app

client = TestClient(app)


def _prep_tenant():
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"doc-tenant-{uuid.uuid4().hex[:8]}"
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


def test_document_crud_and_isolation():
    tenant_id = _prep_tenant()
    _override_user(tenant_id)

    # create
    payload = {"title": "Policy", "content": "GDPR policy text", "category": "policy", "version": 1}
    r = client.post("/api/documents/", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    doc_id = doc["id"]

    # list
    r = client.get("/api/documents/")
    assert r.status_code == 200
    assert any(d["id"] == doc_id for d in r.json())

    # get
    r = client.get(f"/api/documents/{doc_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Policy"

    # update
    r = client.put(f"/api/documents/{doc_id}", json={"title": "Updated"})
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"

    # delete
    r = client.delete(f"/api/documents/{doc_id}")
    assert r.status_code == 200
    r = client.get(f"/api/documents/{doc_id}")
    assert r.status_code == 404

    # isolation: another tenant cannot access
    other_tid = _prep_tenant()
    _override_user(other_tid, user_id=2)
    r = client.get(f"/api/documents/{doc_id}")
    assert r.status_code == 404
    app.dependency_overrides.clear()
