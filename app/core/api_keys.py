from datetime import datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.api_key import ApiKey
from app.services.api_key_service import authenticate_api_key


async def require_api_key(
    x_api_key: str = Header(default=None, alias="X-API-Key"),
    x_tenant_id: int = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not x_api_key or not x_tenant_id:
        raise HTTPException(status_code=401, detail="API key and tenant headers are required.")
    api_key = await authenticate_api_key(db, int(x_tenant_id), x_api_key)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expired.")
    return api_key
