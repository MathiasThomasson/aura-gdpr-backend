from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.auth import require_role, get_current_user
from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.models.user import UserCreate, UserUpdate
from app.services.user_service import create_user_in_tenant, list_users, update_user
from app.core.security import hash_password

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me")
async def get_me(ctx: CurrentContext = Depends(current_context)):
    return {"id": ctx.user.id, "email": ctx.user.email, "tenant_id": ctx.user.tenant_id, "role": ctx.user.role}


@router.patch("/me")
async def patch_me(payload: UserUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # allow user to update own email or password only
    if payload.email is not None:
        current_user.email = payload.email
    if payload.password is not None:
        current_user.hashed_password = hash_password(payload.password)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    await log_event(db, current_user.tenant_id, current_user.id, "user", current_user.id, "update_profile", None)
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}


@router.get("/")
async def list_users_route(db: AsyncSession = Depends(get_db), current_user=Depends(require_role("owner", "admin"))):
    users = await list_users(db, current_user.tenant_id)
    return [{"id": u.id, "email": u.email, "role": u.role} for u in users]


@router.post("/")
async def create_user_route(payload: UserCreate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("owner", "admin"))):
    user = await create_user_in_tenant(db, current_user.tenant_id, payload.email, payload.password, payload.role)
    await log_event(db, current_user.tenant_id, current_user.id, "user", user.id, "create", None)
    return {"id": user.id, "email": user.email, "role": user.role}


@router.patch("/{user_id}")
async def patch_user(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db), ctx=Depends(require_role("owner", "admin"))):
    target = await update_user(
        db,
        tenant_id=ctx.tenant_id if hasattr(ctx, "tenant_id") else ctx.user.tenant_id,
        user_id=user_id,
        email=payload.email,
        password=payload.password,
        role=payload.role if hasattr(payload, "role") else None,
    )
    tenant_id = ctx.tenant_id if hasattr(ctx, "tenant_id") else ctx.user.tenant_id
    actor_id = ctx.id if hasattr(ctx, "id") else getattr(ctx, "user", ctx).id
    await log_event(db, tenant_id, actor_id, "user", target.id, "update", None)
    return {"id": target.id, "email": target.email, "role": target.role}
