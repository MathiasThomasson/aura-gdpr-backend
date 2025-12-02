import sqlite3
import uuid
from typing import Tuple

from app.core.security import hash_password


def create_tenant_and_user(role: str = "owner") -> Tuple[int, int, str]:
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    tenant_name = f"tenant-{uuid.uuid4().hex[:8]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (tenant_name,))
    tenant_id = cur.lastrowid
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (email, hash_password("pwd"), tenant_id, role, "active", 1),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id, user_id, email


def override_user_dependency(app, get_current_user, tenant_id: int, user_id: int, role: str = "owner", email: str | None = None):
    class DummyUser:
        def __init__(self, uid, tid, r, eml):
            self.id = uid
            self.tenant_id = tid
            self.role = r
            self.email = eml or "user@example.com"

    dummy = DummyUser(user_id, tenant_id, role, email)
    app.dependency_overrides[get_current_user] = lambda: dummy
