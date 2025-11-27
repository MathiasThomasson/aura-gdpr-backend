import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.security import create_access_token
from app.core.config import settings
from app.core.ai_audit import log_ai_call
from main import app


client = TestClient(app)


def test_ai_max_input_enforced():
    token = create_access_token({"sub": "1", "tenant_id": 1, "role": "owner"})
    too_long = "x" * (settings.AI_MAX_INPUT_CHARS + 100)
    r = client.post("/api/ai/gdpr/analyze", json={"text": too_long}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_circuit_reset_requires_admin():
    # user token with role user should be forbidden
    token_user = create_access_token({"sub": "2", "tenant_id": 1, "role": "user"})
    r = client.post("/api/ai/circuit/reset", headers={"Authorization": f"Bearer {token_user}"})
    assert r.status_code == 403

    token_admin = create_access_token({"sub": "3", "tenant_id": 1, "role": "admin"})
    r = client.post("/api/ai/circuit/reset", headers={"Authorization": f"Bearer {token_admin}"})
    assert r.status_code in (200, 503, 502)


@pytest.mark.asyncio
async def test_ai_audit_hashes_input(get_test_db):
    # AI_DISABLE_PROMPT_STORAGE defaults to True -> only hash
    async for db in get_test_db():
        await log_ai_call(db, tenant_id=1, user_id=1, input_text="secret-text", model="test", endpoint="/api/ai/gdpr/analyze", high_risk=False, status="success")
        res = await db.execute("SELECT meta FROM audit_logs ORDER BY id DESC LIMIT 1")
        row = res.fetchone()
        assert row is not None
        meta = row[0]
        assert "input_hash_sha256" in meta
        assert "secret-text" not in str(meta)
        break
