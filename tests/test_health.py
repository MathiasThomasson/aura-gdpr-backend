from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_system_ping():
    resp = client.get("/api/system/ping")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
