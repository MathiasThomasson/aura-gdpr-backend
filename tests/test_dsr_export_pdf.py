from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def _create_dsr(tenant_id: int, user_id: int, email: str) -> int:
    override_user_dependency(app, get_current_user, tenant_id, user_id, email=email)
    resp = client.post(
        "/api/dsr/",
        json={
            "request_type": "Access Request",
            "subject_name": "Jane Doe",
            "subject_email": email,
            "description": "Please share all personal data you hold.",
            "priority": "high",
            "source": "internal",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_export_pdf_returns_pdf_for_tenant():
    tenant_id, user_id, email = create_tenant_and_user()
    dsr_id = _create_dsr(tenant_id, user_id, email)

    resp = client.get(f"/api/dsr/{dsr_id}/export-pdf")

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    disposition = resp.headers.get("content-disposition", "")
    assert f'dsr-{dsr_id}.pdf' in disposition
    assert resp.content


def test_export_pdf_isolated_by_tenant():
    tenant_id, user_id, email = create_tenant_and_user()
    dsr_id = _create_dsr(tenant_id, user_id, email)

    other_tenant, other_user, other_email = create_tenant_and_user()
    override_user_dependency(app, get_current_user, other_tenant, other_user, email=other_email)

    resp = client.get(f"/api/dsr/{dsr_id}/export-pdf")
    assert resp.status_code == 404
