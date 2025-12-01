import json
import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import hash_password
from main import app

client = TestClient(app)


def create_tenant_user(role="owner"):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", (f"tenant-{uuid.uuid4().hex[:6]}",))
    tenant_id = cur.lastrowid
    cur.execute(
        "INSERT INTO users (email, hashed_password, tenant_id, role, status, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (f"{uuid.uuid4().hex[:6]}@example.com", hash_password("pwd"), tenant_id, role, "active", 1),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tenant_id, user_id


def override_user(user_id, tenant_id, role):
    class Dummy:
        def __init__(self, uid, tid, r):
            self.id = uid
            self.tenant_id = tid
            self.role = r
            self.email = "dummy@example.com"

    app.dependency_overrides[get_current_user] = lambda: Dummy(user_id, tenant_id, role)


def insert_plan(tenant_id, plan_type="pro"):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tenant_plans (tenant_id, plan_type, name, price_per_month, currency, is_trial, features) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tenant_id, plan_type, plan_type.title(), 5000, "USD", 0, json.dumps(["feature"]))  # type: ignore[arg-type]
    )
    conn.commit()
    conn.close()


def insert_invoice(tenant_id, amount=1000):
    conn = sqlite3.connect("dev.db", timeout=5)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO billing_invoices (tenant_id, amount, currency, description, status, invoice_url) VALUES (?, ?, ?, ?, ?, ?)",
        (tenant_id, amount, "USD", "Test invoice", "paid", "https://billing.example.com/invoice/test"),
    )
    conn.commit()
    conn.close()


def test_billing_plan_respects_tenant_and_role():
    tenant_id, owner_id = create_tenant_user(role="owner")
    other_tenant, _ = create_tenant_user(role="owner")
    insert_plan(tenant_id, "pro")
    insert_plan(other_tenant, "free")

    override_user(owner_id, tenant_id, "owner")
    resp = client.get("/api/billing/plan")
    assert resp.status_code == 200
    assert resp.json()["type"] == "pro"


def test_billing_usage_requires_admin_or_owner():
    tenant_id, user_id = create_tenant_user(role="user")
    override_user(user_id, tenant_id, "user")
    resp = client.get("/api/billing/usage")
    assert resp.status_code == 403


def test_invoices_and_portal_return_data():
    tenant_id, owner_id = create_tenant_user(role="owner")
    insert_invoice(tenant_id, 2500)
    override_user(owner_id, tenant_id, "owner")

    invoices = client.get("/api/billing/invoices")
    assert invoices.status_code == 200
    data = invoices.json()
    assert data["total"] >= 1
    assert data["items"][0]["amount"] == 2500

    portal = client.post("/api/billing/portal")
    assert portal.status_code == 200
    assert str(tenant_id) in portal.json()["url"]
