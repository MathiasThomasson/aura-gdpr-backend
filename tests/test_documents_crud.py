from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def test_documents_crud_and_tenant_isolation():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user_dependency(app, get_current_user, tenant_id, user_id)

    create = client.post("/api/documents/", json={"title": "Doc A", "description": "Desc", "status": "draft"})
    assert create.status_code == 200, create.text
    doc_id = create.json()["id"]

    listing = client.get("/api/documents/")
    assert listing.status_code == 200
    assert any(item["id"] == doc_id for item in listing.json())

    detail = client.get(f"/api/documents/{doc_id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Doc A"

    updated = client.patch(f"/api/documents/{doc_id}", json={"title": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated"

    deleted = client.delete(f"/api/documents/{doc_id}")
    assert deleted.status_code == 200

    missing = client.get(f"/api/documents/{doc_id}")
    assert missing.status_code == 404

    other_tenant, other_user, _ = create_tenant_and_user()
    override_user_dependency(app, get_current_user, other_tenant, other_user)
    forbidden = client.get(f"/api/documents/{doc_id}")
    assert forbidden.status_code == 404
