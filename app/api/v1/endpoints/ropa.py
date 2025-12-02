from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.ropa import ROPARecordCreate, ROPARecordOut, ROPARecordUpdate
from app.services.ropa_service import create_ropa, delete_ropa, get_ropa, list_ropa, update_ropa

router = APIRouter(prefix="/api/ropa", tags=["ROPA"])


@router.get("", response_model=list[ROPARecordOut], summary="List ROPA records")
async def list_ropa_items(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await list_ropa(db, ctx.tenant_id)


@router.post("", response_model=ROPARecordOut, status_code=201, summary="Create ROPA record")
async def create_ropa_item(
    payload: ROPARecordCreate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await create_ropa(db, ctx.tenant_id, payload)


@router.get("/{record_id}", response_model=ROPARecordOut, summary="Get ROPA record")
async def get_ropa_item(
    record_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await get_ropa(db, ctx.tenant_id, record_id)


@router.patch("/{record_id}", response_model=ROPARecordOut, summary="Update ROPA record")
async def update_ropa_item(
    record_id: int, payload: ROPARecordUpdate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await update_ropa(db, ctx.tenant_id, record_id, payload)


@router.delete("/{record_id}", summary="Delete ROPA record")
async def delete_ropa_item(
    record_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await delete_ropa(db, ctx.tenant_id, record_id)
