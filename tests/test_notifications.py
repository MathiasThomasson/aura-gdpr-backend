import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app

client = TestClient(app)


def create_tenant_and_user(role="user", tenant_id=None):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    if tenant_id is None:
        name = f"tenant-{uuid.uuid4().hex[:6]}"
        cur.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
        tenant_id = cur.lastrowid
    email = f"{uuid.uuid4().hex[:6]}@example.com"
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (email, hash_password("pwd"), tenant_id, role, "active", 1),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id, user_id, email


def create_notification(tenant_id, user_id=None, title="n", read=False):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (tenant_id, user_id, type, title, description, severity, read) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tenant_id, user_id, "system_health", title, "desc", "info", 1 if read else 0),
    )
    notif_id = cur.lastrowid
    conn.commit()
    conn.close()
    return notif_id


def override_user(user_id, tenant_id, role):
    class Dummy:
        def __init__(self, uid, tid, r):
            self.id = uid
            self.tenant_id = tid
            self.role = r
            self.email = "dummy@example.com"

    app.dependency_overrides[get_current_user] = lambda: Dummy(user_id, tenant_id, role)


def test_notifications_respect_tenant_isolation():
    t1, u1, _ = create_tenant_and_user(role="user")
    t2, u2, _ = create_tenant_and_user(role="user")

    create_notification(t1, u1, title="mine")
    create_notification(t2, u2, title="other-tenant")

    override_user(u1, t1, "user")
    resp = client.get("/api/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert all(item["tenant_id"] == t1 for item in data["items"])


def test_notification_visibility_differs_by_role():
    tenant_id, owner_id, _ = create_tenant_and_user(role="owner")
    _, user_a_id, _ = create_tenant_and_user(role="user", tenant_id=tenant_id)
    _, user_b_id, _ = create_tenant_and_user(role="user", tenant_id=tenant_id)

    create_notification(tenant_id, None, title="tenant-wide")
    create_notification(tenant_id, user_a_id, title="for-a")
    create_notification(tenant_id, user_b_id, title="for-b")

    override_user(user_a_id, tenant_id, "user")
    resp_user = client.get("/api/notifications")
    assert resp_user.status_code == 200
    titles = {item["title"] for item in resp_user.json()["items"]}
    assert "for-a" in titles
    assert "tenant-wide" in titles
    assert "for-b" not in titles

    override_user(owner_id, tenant_id, "owner")
    resp_owner = client.get("/api/notifications")
    assert resp_owner.status_code == 200
    titles_owner = {item["title"] for item in resp_owner.json()["items"]}
    assert {"for-a", "for-b", "tenant-wide"}.issubset(titles_owner)


def test_mark_all_read_scopes_to_user_and_tenant():
    tenant_id, user_a_id, _ = create_tenant_and_user(role="user")
    _, user_b_id, _ = create_tenant_and_user(role="user", tenant_id=tenant_id)
    other_tenant, other_user_id, _ = create_tenant_and_user(role="user")

    n1 = create_notification(tenant_id, user_a_id, title="a1")
    n2 = create_notification(tenant_id, None, title="tenant")
    n3 = create_notification(tenant_id, user_b_id, title="b1")
    n_other = create_notification(other_tenant, other_user_id, title="other")

    override_user(user_a_id, tenant_id, "user")
    resp = client.post("/api/notifications/mark-all-read")
    assert resp.status_code == 200
    assert resp.json()["updated"] >= 2

    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute("SELECT id, read FROM notifications WHERE id IN (?, ?, ?, ?)", (n1, n2, n3, n_other))
    rows = cur.fetchall()
    conn.close()
    reads = {row[0]: row[1] for row in rows}
    assert reads[n1] == 1
    assert reads[n2] == 1  # tenant-wide marked
    assert reads[n3] == 0  # other user in same tenant not affected
    assert reads[n_other] == 0  # other tenant untouched
