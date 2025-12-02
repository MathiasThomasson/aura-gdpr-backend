from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.cookie import CookieCreate, CookieOut, CookieUpdate
from app.services.cookie_service import create_cookie, delete_cookie, get_cookie, list_cookies, update_cookie

router = APIRouter(prefix="/api/cookies", tags=["Cookies"])


@router.get("", response_model=list[CookieOut], summary="List cookies")
async def list_cookie_items(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await list_cookies(db, ctx.tenant_id)


@router.post("", response_model=CookieOut, status_code=201, summary="Create cookie")
async def create_cookie_item(
    payload: CookieCreate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await create_cookie(db, ctx.tenant_id, payload)


@router.get("/{cookie_id}", response_model=CookieOut, summary="Get cookie")
async def get_cookie_item(
    cookie_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await get_cookie(db, ctx.tenant_id, cookie_id)


@router.patch("/{cookie_id}", response_model=CookieOut, summary="Update cookie")
async def update_cookie_item(
    cookie_id: int, payload: CookieUpdate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await update_cookie(db, ctx.tenant_id, cookie_id, payload)


@router.delete("/{cookie_id}", summary="Delete cookie")
async def delete_cookie_item(
    cookie_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await delete_cookie(db, ctx.tenant_id, cookie_id)
