from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import create_project, delete_project, get_project, list_projects, update_project

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectOut], summary="List projects")
async def list_project_items(ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)):
    return await list_projects(db, ctx.tenant_id)


@router.post("", response_model=ProjectOut, status_code=201, summary="Create project")
async def create_project_item(
    payload: ProjectCreate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await create_project(db, ctx.tenant_id, payload)


@router.get("/{project_id}", response_model=ProjectOut, summary="Get project")
async def get_project_item(
    project_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await get_project(db, ctx.tenant_id, project_id)


@router.patch("/{project_id}", response_model=ProjectOut, summary="Update project")
async def update_project_item(
    project_id: int, payload: ProjectUpdate, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await update_project(db, ctx.tenant_id, project_id, payload)


@router.delete("/{project_id}", summary="Delete project")
async def delete_project_item(
    project_id: int, ctx: CurrentContext = Depends(current_context), db: AsyncSession = Depends(get_db)
):
    return await delete_project(db, ctx.tenant_id, project_id)
