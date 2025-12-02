from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def test_dpia_crud_and_isolation():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user_dependency(app, get_current_user, tenant_id, user_id)

    created = client.post("/api/dpia", json={"title": "DPIA A"})
    assert created.status_code == 201
    item_id = created.json()["id"]

    listing = client.get("/api/dpia")
    assert listing.status_code == 200
    assert any(i["id"] == item_id for i in listing.json())

    detail = client.get(f"/api/dpia/{item_id}")
    assert detail.status_code == 200

    updated = client.patch(f"/api/dpia/{item_id}", json={"status": "in_progress"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    client.delete(f"/api/dpia/{item_id}")
    override_user_dependency(app, get_current_user, *create_tenant_and_user()[:2])
    assert client.get(f"/api/dpia/{item_id}").status_code == 404
