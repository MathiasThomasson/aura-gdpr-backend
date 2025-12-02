from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def test_ropa_crud_and_isolation():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user_dependency(app, get_current_user, tenant_id, user_id)

    created = client.post("/api/ropa", json={"title": "Record A"})
    assert created.status_code == 201
    item_id = created.json()["id"]

    assert client.get("/api/ropa").status_code == 200

    detail = client.get(f"/api/ropa/{item_id}")
    assert detail.status_code == 200

    updated = client.patch(f"/api/ropa/{item_id}", json={"description": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"

    client.delete(f"/api/ropa/{item_id}")
    override_user_dependency(app, get_current_user, *create_tenant_and_user()[:2])
    assert client.get(f"/api/ropa/{item_id}").status_code == 404
