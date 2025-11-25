from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user, require_role
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from sqlalchemy.future import select
from app.db.models.user import User
from app.models.user import UserCreate, UserUpdate
from app.core.security import hash_password
from app.core.audit import log_event

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "tenant_id": current_user.tenant_id, "role": current_user.role}


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
async def list_users(db: AsyncSession = Depends(get_db), current_user=Depends(require_role("owner", "admin"))):
    # list users in the tenant (owner/admin only)
    result = await db.execute(select(User).where(User.tenant_id == current_user.tenant_id))
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email, "role": u.role} for u in users]


@router.post("/")
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("owner", "admin"))):
    # admin/owner creates user within their tenant; tenant_id must come from current_user
    user = User(email=payload.email, hashed_password=hash_password(payload.password), tenant_id=current_user.tenant_id, role=payload.role or "user")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await log_event(db, current_user.tenant_id, current_user.id, "user", user.id, "create", None)
    return {"id": user.id, "email": user.email, "role": user.role}


@router.patch("/{user_id}")
async def patch_user(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("owner", "admin"))):
    # owner/admin can update role or email of users in same tenant (but not change tenant_id)
    target = await db.get(User, user_id)
    if not target or target.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    # only role change allowed here via owner/admin; disallow tenant_id change
    if payload.email is not None:
        target.email = payload.email
    if payload.password is not None:
        target.hashed_password = hash_password(payload.password)
    db.add(target)
    await db.commit()
    await db.refresh(target)
    await log_event(db, current_user.tenant_id, current_user.id, "user", target.id, "update", None)
    return {"id": target.id, "email": target.email, "role": target.role}
