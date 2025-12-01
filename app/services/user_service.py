from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import ALLOWED_ROLES
from app.core.security import hash_password
from app.db.models.user import User
from app.repositories.user_repository import get_user_in_tenant, list_users_in_tenant, save_user


async def list_users(db: AsyncSession, tenant_id: int):
    return await list_users_in_tenant(db, tenant_id)


async def create_user_in_tenant(db: AsyncSession, tenant_id: int, email: str, password: str, role: str | None):
    role_final = role or "user"
    if role_final not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    user = User(
        email=email,
        hashed_password=hash_password(password),
        tenant_id=tenant_id,
        role=role_final,
        status="active",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    email: str | None,
    password: str | None,
    role: str | None,
):
    user = await get_user_in_tenant(db, tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role is not None:
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role
    if email is not None:
        user.email = email
    if password is not None:
        user.hashed_password = hash_password(password)
    return await save_user(db, user)
