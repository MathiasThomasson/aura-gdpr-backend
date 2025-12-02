from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.dpia import DPIACreate, DPIAOut, DPIAUpdate
from app.services.dpia_service import create_dpia, delete_dpia, get_dpia, list_dpia, update_dpia

router = APIRouter(prefix="/api/dpia", tags=["DPIA"])


@router.get("", response_model=list[DPIAOut], summary="List DPIAs")
async def list_dpia_items(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await list_dpia(db, ctx.tenant_id)


@router.post("", response_model=DPIAOut, status_code=201, summary="Create DPIA")
async def create_dpia_item(
    payload: DPIACreate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await create_dpia(db, ctx.tenant_id, payload)


@router.get("/{dpia_id}", response_model=DPIAOut, summary="Get DPIA")
async def get_dpia_item(dpia_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await get_dpia(db, ctx.tenant_id, dpia_id)


@router.patch("/{dpia_id}", response_model=DPIAOut, summary="Update DPIA")
async def update_dpia_item(
    dpia_id: int, payload: DPIAUpdate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await update_dpia(db, ctx.tenant_id, dpia_id, payload)


@router.delete("/{dpia_id}", summary="Delete DPIA")
async def delete_dpia_item(dpia_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await delete_dpia(db, ctx.tenant_id, dpia_id)
