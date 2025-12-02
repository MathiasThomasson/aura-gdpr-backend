from datetime import datetime

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from main import app
from tests.utils import create_tenant_and_user, override_user_dependency

client = TestClient(app)


def test_tasks_crud_minimal():
    tenant_id, user_id, _ = create_tenant_and_user()
    override_user_dependency(app, get_current_user, tenant_id, user_id)

    created = client.post("/api/tasks", json={"title": "Task A", "due_date": datetime.utcnow().isoformat()})
    assert created.status_code == 200
    task_id = created.json()["id"]

    listing = client.get("/api/tasks")
    assert listing.status_code == 200
    assert any(i["id"] == task_id for i in listing.json())

    detail = client.get(f"/api/tasks/{task_id}")
    assert detail.status_code == 200

    updated = client.patch(f"/api/tasks/{task_id}", json={"status": "completed"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"

    client.delete(f"/api/tasks/{task_id}")
    override_user_dependency(app, get_current_user, *create_tenant_and_user()[:2])
    assert client.get(f"/api/tasks/{task_id}").status_code == 404
