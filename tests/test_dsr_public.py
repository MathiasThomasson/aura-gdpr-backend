from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def test_public_dsr_flow_creates_record():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user_dependency(app, get_current_user, tenant_id, user_id)

    link = client.post("/api/dsr/public-link/enable")
    assert link.status_code == 200
    public_url = link.json()["public_url"]
    assert public_url
    public_key = public_url.rstrip("/").split("/")[-1]

    payload = {
        "request_type": "Access",
        "subject_name": "Alice",
        "subject_email": "alice@example.com",
        "description": "Please share data",
        "priority": "medium",
    }
    public_resp = client.post(f"/api/public/dsr/{public_key}", json=payload)
    assert public_resp.status_code == 201

    authed_list = client.get("/api/dsr?limit=10")
    assert authed_list.status_code == 200
    items = authed_list.json()
    assert any(i["subject_email"] == "alice@example.com" and i["source"] == "public_form" for i in items)
