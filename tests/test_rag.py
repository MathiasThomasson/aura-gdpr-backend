import pytest
from fastapi.testclient import TestClient
from main import app
import sqlite3
from app.core.security import hash_password
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings as cfg

client = TestClient(app)


@pytest.mark.asyncio
async def test_rag_create_and_list_documents():
    # create tenant and user
    conn = sqlite3.connect("dev.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO tenants (name) VALUES (?)", ("rag-tenant",))
    tenant_id = cur.lastrowid
    h = hash_password("pwd")
    cur.execute("INSERT INTO users (email, hashed_password, tenant_id, role) VALUES (?, ?, ?, ?)", ("raguser@example.com", h, tenant_id, "owner"))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    headers = {"Authorization": "", "X-Tenant-Id": str(tenant_id), "X-User-Id": str(user_id)}

    payload = {"title": "Doc1", "content": "# Section One\nThis is a sample doc.", "source": "internal_policy", "language": "sv", "tags": ["policy"]}
    # override get_current_user: create a dummy owner
    class DummyOwner:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id
            self.role = "owner"

    app.dependency_overrides = {}
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: DummyOwner(user_id, tenant_id)
    # Override get_db for this route to use a real async session
    from app.db.database import get_db as real_get_db
    async def override_get_db():
        engine = create_async_engine(cfg.DATABASE_URL, echo=False)
        AsyncSessionLocal2 = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with AsyncSessionLocal2() as sess_override:
            yield sess_override
    app.dependency_overrides[real_get_db] = override_get_db

    r = client.post("/api/rag/documents", json=payload)
    assert r.status_code == 200
    doc = r.json()
    assert doc["title"] == "Doc1"

    r2 = client.get("/api/rag/documents")
    assert r2.status_code == 200
    docs = r2.json()
    assert any(d["title"] == "Doc1" for d in docs)

    # search
    r3 = client.post("/api/rag/search", json={"query": "sample"})
    assert r3.status_code == 200
    data = r3.json()
    assert "citations" in data
    assert data["citations"]

    app.dependency_overrides.clear()
