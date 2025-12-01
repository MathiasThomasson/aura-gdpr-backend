import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models.api_key import ApiKey


async def create_api_key(db: AsyncSession, tenant_id: int, name: str, expires_at: Optional[datetime] = None) -> tuple[ApiKey, str]:
    raw_key = secrets.token_urlsafe(32)
    key_hash = hash_password(raw_key)
    api_key = ApiKey(tenant_id=tenant_id, name=name, key_hash=key_hash, expires_at=expires_at)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


async def list_api_keys(db: AsyncSession, tenant_id: int) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).where(ApiKey.tenant_id == tenant_id))
    return result.scalars().all()


async def delete_api_key(db: AsyncSession, tenant_id: int, api_key_id: int) -> None:
    api_key = await db.get(ApiKey, api_key_id)
    if not api_key or api_key.tenant_id != tenant_id:
        raise ValueError("API key not found")
    await db.delete(api_key)
    await db.commit()


async def authenticate_api_key(db: AsyncSession, tenant_id: int, raw_key: str) -> Optional[ApiKey]:
    result = await db.execute(select(ApiKey).where(ApiKey.tenant_id == tenant_id))
    for api_key in result.scalars().all():
        if verify_password(raw_key, api_key.key_hash):
            api_key.last_used_at = datetime.utcnow()
            db.add(api_key)
            await db.commit()
            return api_key
    return None
