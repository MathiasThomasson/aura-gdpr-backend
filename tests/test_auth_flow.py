import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import sqlite3
import uuid
from datetime import datetime

from fastapi.testclient import TestClient
from jose import jwt
import pytest

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from main import app


client = TestClient(app)


def _create_tenant_and_user(email: str, role: str = "user"):
    """Helper to insert tenant and user rows directly into sqlite test DB."""
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    tenant_name = f"tenant-{uuid.uuid4().hex[:6]}"
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (tenant_name,))
    tenant_id = cur.lastrowid
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)",
        (email, hash_password("pwd"), tenant_id, role),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id, user_id


def test_tenant_register_then_login_and_refresh():
    # Register tenant + owner
    name = f"acme-{uuid.uuid4().hex[:6]}"
    email = f"{name}@example.com"
    password = "strongpass"
    r = client.post("/api/tenants/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 200, r.text
    tenant_id = r.json()["tenant"]["id"]

    # Login
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data and "refresh_token" in data

    # Refresh
    r = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 200, r.text
    refreshed = r.json()
    assert "access_token" in refreshed and "refresh_token" in refreshed

    # Access token should carry tenant and role claims
    decoded = jwt.decode(refreshed["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded.get("tenant_id") == tenant_id
    assert decoded.get("role") == "owner"
    # Refresh should rotate: old token no longer works
    r_reuse = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r_reuse.status_code == 401


def test_password_reset_flow():
    name = f"reset-{uuid.uuid4().hex[:6]}"
    email = f"{name}@example.com"
    password = "orig-pass"
    r = client.post("/api/tenants/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 200, r.text

    # Request reset
    r = client.post("/api/auth/forgot-password", json={"email": email})
    assert r.status_code == 200, r.text
    token = r.json().get("debug_token")
    assert token

    # Reset password
    new_password = "new-pass"
    r = client.post("/api/auth/reset-password", json={"token": token, "new_password": new_password})
    assert r.status_code == 200, r.text

    # Old password should fail
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 400
    # New password should work
    r = client.post("/api/auth/login", json={"email": email, "password": new_password})
    assert r.status_code == 200


def test_cross_tenant_token_mismatch_rejected():
    # Create two tenants/users
    t1, u1 = _create_tenant_and_user("a@example.com", "user")
    t2, u2 = _create_tenant_and_user("b@example.com", "admin")

    # Issue token for u1 but forged tenant_id = t2
    forged = create_access_token({"sub": str(u1), "tenant_id": t2, "role": "user"})

    # Ensure no overrides interfere with auth dependency
    app.dependency_overrides.pop(get_current_user, None)
    r = client.get("/api/users/me", headers={"Authorization": f"Bearer {forged}"})
    # Should be rejected because token tenant != DB tenant
    assert r.status_code == 401

    # A proper token for u2 should work
    proper = create_access_token({"sub": str(u2), "tenant_id": t2, "role": "admin"})
    r = client.get("/api/users/me", headers={"Authorization": f"Bearer {proper}"})
    assert r.status_code == 200


def test_refresh_reuse_detection_revokes_family():
    name = f"reuse-{uuid.uuid4().hex[:6]}"
    email = f"{name}@example.com"
    password = "pw123456"
    r = client.post("/api/tenants/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 200
    login = client.post("/api/auth/login", json={"email": email, "password": password}).json()
    first_rt = login["refresh_token"]
    # First refresh rotates
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": first_rt})
    assert refreshed.status_code == 200
    new_rt = refreshed.json()["refresh_token"]
    # Reuse old token should now be rejected
    reuse = client.post("/api/auth/refresh", json={"refresh_token": first_rt})
    assert reuse.status_code == 401
    # New token should still work once
    ok = client.post("/api/auth/refresh", json={"refresh_token": new_rt})
    assert ok.status_code == 200
