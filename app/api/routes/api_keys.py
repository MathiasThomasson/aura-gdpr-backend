from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_role
from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.api_keys import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyOut
from app.services.api_key_service import create_api_key, delete_api_key, list_api_keys

router = APIRouter(prefix="/api/apikeys", tags=["API Keys"])


@router.post("/", response_model=ApiKeyCreateResponse, summary="Create API key", description="Create a new API key for the current tenant.")
async def create_api_key_endpoint(
    payload: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
    _: None = Depends(require_role("admin", "owner", "superadmin")),
):
    api_key, raw_key = await create_api_key(db, ctx.tenant_id, payload.name, payload.expires_at)
    api_key_data = ApiKeyOut.model_validate(api_key).model_dump()
    return ApiKeyCreateResponse(key=raw_key, **api_key_data)


@router.get("/", response_model=list[ApiKeyOut], summary="List API keys", description="List all API keys for the current tenant.")
async def list_api_keys_endpoint(
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    keys = await list_api_keys(db, ctx.tenant_id)
    return keys


@router.delete("/{api_key_id}", status_code=204, summary="Delete API key", description="Delete an API key by id.")
async def delete_api_key_endpoint(
    api_key_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
    _: None = Depends(require_role("admin", "owner", "superadmin")),
):
    try:
        await delete_api_key(db, ctx.tenant_id, api_key_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="API key not found")
    return None
