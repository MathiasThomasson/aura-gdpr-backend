import sqlite3
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app


client = TestClient(app)


def _prep_tenant_with_user():
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"gdpr-{uuid.uuid4().hex[:6]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
    tid = cur.lastrowid
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)",
        (f"{name}@example.com", hash_password("pwd"), tid, "owner"),
    )
    uid = cur.lastrowid
    conn.commit()
    conn.close()
    return tid, uid


def _override_user(tenant_id: int, user_id: int):
    class DummyUser:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "owner"

    dummy = DummyUser(user_id, tenant_id)
    app.dependency_overrides[get_current_user] = lambda: dummy


def test_gdpr_export_and_delete_user():
    tid, uid = _prep_tenant_with_user()
    _override_user(tid, uid)

    # add a task
    client.post("/api/tasks/", json={"title": "Do", "status": "open"})
    # export
    r = client.get(f"/api/gdpr/export/user/{uid}")
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["id"] == uid
    # delete/anonymize user
    r = client.post(f"/api/gdpr/delete/user/{uid}")
    assert r.status_code == 200
    # re-export should still work (user email anonymized)
    r = client.get(f"/api/gdpr/export/user/{uid}")
    assert r.status_code == 200


def test_gdpr_export_and_delete_tenant():
    tid, uid = _prep_tenant_with_user()
    _override_user(tid, uid)
    # export tenant
    r = client.get(f"/api/gdpr/export/tenant/{tid}")
    assert r.status_code == 200
    # delete tenant data
    r = client.post(f"/api/gdpr/delete/tenant/{tid}")
    assert r.status_code == 200
    # access after delete should 403/404
    r = client.get(f"/api/gdpr/export/tenant/{tid}")
    assert r.status_code in (403, 404)


def test_retention_stub_runs():
    # basic call to retention service
    from app.services.retention_service import apply_retention
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    import os
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def run():
        async with SessionLocal() as session:
            await apply_retention(session)

    import asyncio
    asyncio.get_event_loop().run_until_complete(run())
