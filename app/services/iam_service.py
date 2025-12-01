from datetime import datetime, timezone
import secrets
from typing import List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import ALLOWED_ROLES
from app.core.security import hash_password
from app.db.models.user import User
from app.schemas.iam import ALLOWED_IAM_STATUSES, InviteUserRequest, IamUserUpdate


async def _get_user(db: AsyncSession, tenant_id: int, user_id: int) -> User:
    res = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def list_users(db: AsyncSession, tenant_id: int) -> List[User]:
    res = await db.execute(select(User).where(User.tenant_id == tenant_id))
    return res.scalars().all()


async def invite_user(db: AsyncSession, tenant_id: int, payload: InviteUserRequest) -> User:
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    placeholder_password = hash_password(secrets.token_hex(8))
    now = datetime.now(timezone.utc)
    user = User(
        tenant_id=tenant_id,
        email=payload.email,
        hashed_password=placeholder_password,
        full_name=payload.name,
        role=payload.role,
        status="pending_invite",
        is_active=False,
        invited_at=now,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, tenant_id: int, user_id: int, payload: IamUserUpdate) -> User:
    user = await _get_user(db, tenant_id, user_id)
    if payload.role and payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if payload.name is not None:
        user.full_name = payload.name
    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        await apply_status(user, payload.status)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def apply_status(user: User, status: str) -> None:
    if status not in ALLOWED_IAM_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if status == "active":
        user.status = "active"
        user.is_active = True
    elif status == "disabled":
        user.status = "disabled"
        user.is_active = False
    elif status == "pending_invite":
        user.status = "pending_invite"
        user.is_active = False
    user.updated_at = datetime.now(timezone.utc)


async def patch_user(db: AsyncSession, tenant_id: int, user_id: int, payload: IamUserUpdate) -> User:
    user = await _get_user(db, tenant_id, user_id)
    if payload.status:
        await apply_status(user, payload.status)
    if payload.action == "resend_invite":
        user.status = "pending_invite"
        user.invited_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def to_read_model(user: User):
    return {
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
        "role": user.role,
        "status": getattr(user, "status", "active"),
        "last_login": getattr(user, "last_login_at", None),
        "created_at": user.created_at,
    }
