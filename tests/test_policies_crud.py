from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def test_policy_crud_and_isolation():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user_dependency(app, get_current_user, tenant_id, user_id)

    created = client.post("/api/policies", json={"title": "Policy A", "status": "draft"})
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    listing = client.get("/api/policies")
    assert listing.status_code == 200
    assert any(i["id"] == item_id for i in listing.json())

    detail = client.get(f"/api/policies/{item_id}")
    assert detail.status_code == 200

    updated = client.patch(f"/api/policies/{item_id}", json={"description": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"

    deleted = client.delete(f"/api/policies/{item_id}")
    assert deleted.status_code == 200

    override_user_dependency(app, get_current_user, *create_tenant_and_user()[:2])
    missing = client.get(f"/api/policies/{item_id}")
    assert missing.status_code == 404
