from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def test_incident_crud_and_isolation():
    tenant_id, user_id, email = create_tenant_and_user()
    override_user_dependency(app, get_current_user, tenant_id, user_id, email=email)

    created = client.post("/api/incidents", json={"title": "Breach", "severity": "high", "description": "Test"})
    assert created.status_code == 201
    incident_id = created.json()["id"]

    listing = client.get("/api/incidents")
    assert listing.status_code == 200
    assert any(i["id"] == incident_id for i in listing.json())

    detail = client.get(f"/api/incidents/{incident_id}")
    assert detail.status_code == 200

    updated = client.patch(f"/api/incidents/{incident_id}", json={"status": "closed"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "closed"

    client.delete(f"/api/incidents/{incident_id}")
    override_user_dependency(app, get_current_user, *create_tenant_and_user()[:2])
    assert client.get(f"/api/incidents/{incident_id}").status_code == 404
