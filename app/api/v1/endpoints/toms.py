from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.tom import TOMCreate, TOMOut, TOMUpdate
from app.services.tom_service import create_tom, delete_tom, get_tom, list_toms, update_tom

router = APIRouter(prefix="/api/toms", tags=["TOMs"])


@router.get("", response_model=list[TOMOut], summary="List TOMs")
async def list_tom_items(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await list_toms(db, ctx.tenant_id)


@router.post("", response_model=TOMOut, status_code=201, summary="Create TOM")
async def create_tom_item(
    payload: TOMCreate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await create_tom(db, ctx.tenant_id, payload)


@router.get("/{tom_id}", response_model=TOMOut, summary="Get TOM")
async def get_tom_item(tom_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await get_tom(db, ctx.tenant_id, tom_id)


@router.patch("/{tom_id}", response_model=TOMOut, summary="Update TOM")
async def update_tom_item(
    tom_id: int, payload: TOMUpdate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await update_tom(db, ctx.tenant_id, tom_id, payload)


@router.delete("/{tom_id}", summary="Delete TOM")
async def delete_tom_item(tom_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await delete_tom(db, ctx.tenant_id, tom_id)
