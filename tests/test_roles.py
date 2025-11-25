from fastapi.testclient import TestClient
from main import app
import sqlite3
import uuid
from app.core.auth import get_current_user
from app.core.security import hash_password

client = TestClient(app)


def create_tenant_and_user(name_suffix, email, role):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    name = f"tenant-{name_suffix}-{uuid.uuid4().hex[:6]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
    tenant_id = cur.lastrowid
    # create a user row
    h = hash_password("pwd")
    try:
        cur.execute("INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)", (email, h, tenant_id, role))
        user_id = cur.lastrowid
    except Exception:
        # if email already exists, select that user id
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        user_id = row[0] if row else None
    conn.commit()
    conn.close()
    return tenant_id, user_id


def test_user_cannot_access_admin_endpoints():
    tenant_id, user_id = create_tenant_and_user("u1", "normal@example.com", "user")
    class DummyUser:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "user"

    app.dependency_overrides[get_current_user] = lambda: DummyUser(user_id, tenant_id)

    # user tries to list users => 403
    r = client.get("/api/users/")
    assert r.status_code == 403


def test_admin_and_owner_can_list_and_create_users():
    tenant_id, owner_id = create_tenant_and_user("a1", "owner@example.com", "owner")

    class Owner:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "owner"

    app.dependency_overrides[get_current_user] = lambda: Owner(owner_id, tenant_id)

    # owner can create a new user (use unique email to avoid collisions)
    new_email = f"new-{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/users/", json={"email": new_email, "password": "pwd", "role": "user"})
    assert r.status_code == 200, r.text
    new = r.json()
    assert new["email"] == new_email

    # owner can list users
    r = client.get("/api/users/")
    assert r.status_code == 200
    users = r.json()
    assert any(u["email"] == new_email for u in users)


def test_tenant_isolation_for_admin_endpoints():
    t1, admin1 = create_tenant_and_user("iso1", "admin1@example.com", "admin")
    t2, admin2 = create_tenant_and_user("iso2", "admin2@example.com", "admin")

    class Admin1:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "admin"

    app.dependency_overrides[get_current_user] = lambda: Admin1(admin1, t1)

    # Admin1 should not see users from tenant 2
    r = client.get("/api/users/")
    assert r.status_code == 200
    users = r.json()
    # ensure admin1 does not see users from tenant 2
    assert all(u.get("email") != "admin2@example.com" for u in users)
