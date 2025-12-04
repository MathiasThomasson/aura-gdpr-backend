from datetime import datetime, timedelta, timezone
import logging
import re
import unicodedata
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.core.roles import Role, ALLOWED_ROLES
from app.db.models.password_reset_token import PasswordResetToken
from app.db.models.refresh_token import RefreshToken
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.models.auth import LoginRequest, RegisterRequest


logger = logging.getLogger("app.auth")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value)
    value = value.strip("-").lower()
    return value or "tenant"


async def _generate_unique_tenant_name(db: AsyncSession, email: str) -> str:
    local = email.split("@")[0] if "@" in email else email
    base = f"{local} Tenant"
    candidate = base
    suffix = 1
    while True:
        existing = await db.execute(select(Tenant).where(Tenant.name == candidate))
        if not existing.scalars().first():
            return candidate
        candidate = f"{base} {suffix}"
        suffix += 1


async def _create_tenant_for_email(db: AsyncSession, email: str) -> Tenant:
    name = await _generate_unique_tenant_name(db, email)
    slug = slugify(name)
    tenant = Tenant(name=name, slug=slug)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def register_user_in_tenant(db: AsyncSession, payload: RegisterRequest) -> User:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    tenant = None
    tenant_id = payload.tenant_id
    created_tenant = False
    try:
        if tenant_id is None:
            tenant = await _create_tenant_for_email(db, payload.email)
            tenant_id = tenant.id
            created_tenant = True
        else:
            tenant = await db.get(Tenant, tenant_id)
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")
        role = payload.role or (Role.OWNER.value if created_tenant else Role.USER.value)
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            tenant_id=tenant_id,
            role=role,
            status="active",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("User registration failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")
    except Exception as exc:
        logger.error("Unexpected error during registration", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


async def issue_token_pair(user: User) -> tuple[str, str, datetime, str]:
    """Return (access_token, refresh_token, refresh_expires, family_id)."""
    access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token, refresh_expires = create_refresh_token()
    family_id = str(uuid.uuid4())
    return access_token, refresh_token, refresh_expires, family_id


async def login_user(db: AsyncSession, payload: LoginRequest) -> tuple[User, str, RefreshToken]:
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalars().first()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        if user.tenant_id is None:
            raise HTTPException(status_code=400, detail="User not assigned to a tenant")
        if getattr(user, "status", "active") == "disabled":
            raise HTTPException(status_code=403, detail="User is disabled")
        if getattr(user, "status", "active") == "pending_invite":
            raise HTTPException(status_code=403, detail="Invitation not accepted yet")

        access_token, refresh_token, refresh_expires, family_id = await issue_token_pair(user)
        rt = RefreshToken(
            user_id=user.id,
            tenant_id=user.tenant_id,
            token=refresh_token,
            family_id=family_id,
            expires_at=refresh_expires,
        )
        db.add(rt)
        user.last_login_at = datetime.now(timezone.utc)
        db.add(user)
        await db.commit()
        return user, access_token, rt
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Login failed due to DB error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error during login", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


async def refresh_session(db: AsyncSession, refresh_token_str: str) -> tuple[str, RefreshToken]:
    now = datetime.now(timezone.utc)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token_str))
    rt = result.scalars().first()
    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # Reuse detection: if already revoked or rotated, revoke family and reject
    if rt.revoked or rt.replaced_by_token:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == rt.family_id)
            .where(RefreshToken.token != rt.replaced_by_token)
            .values(revoked=True, revoked_reason="reuse_detected", last_used_at=now)
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reused or revoked")
    rt_expires = rt.expires_at
    if rt_expires.tzinfo is None:
        rt_expires = rt_expires.replace(tzinfo=timezone.utc)
    if rt_expires < now:
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = await db.get(User, rt.user_id)
    if not user or user.tenant_id != rt.tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token user")

    # Rotate: revoke old, issue new with same family
    new_refresh, new_expires = create_refresh_token()
    access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    )
    rt.revoked = True
    rt.revoked_reason = "rotated"
    rt.replaced_by_token = new_refresh
    rt.last_used_at = now
    new_rt = RefreshToken(
        user_id=user.id,
        tenant_id=user.tenant_id,
        token=new_refresh,
        family_id=rt.family_id,
        expires_at=new_expires,
    )
    db.add(rt)
    db.add(new_rt)
    await db.commit()
    return access_token, new_rt


async def request_password_reset(db: AsyncSession, email: str) -> Optional[str]:
    """Return reset token for dev/test; production would email it."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return None
    token = uuid.uuid4().hex
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    pr = PasswordResetToken(
        user_id=user.id,
        tenant_id=user.tenant_id,
        token=token,
        expires_at=expires,
    )
    db.add(pr)
    await db.commit()
    return token


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == token))
    pr = result.scalars().first()
    if not pr or pr.used:
        raise HTTPException(status_code=400, detail="Invalid token")
    pr_expires = pr.expires_at
    if pr_expires.tzinfo is None:
        pr_expires = pr_expires.replace(tzinfo=timezone.utc)
    if pr_expires < now:
        raise HTTPException(status_code=400, detail="Token expired")
    user = await db.get(User, pr.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token user")
    user.hashed_password = hash_password(new_password)
    pr.used = True
    db.add_all([user, pr])
    await db.commit()
    await log_event(db, user.tenant_id, user.id, "user", user.id, "password_reset", None)
