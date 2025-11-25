from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from app.db.database import get_db
from app.db.models.user import User
from app.db.models.refresh_token import RefreshToken
from app.db.models.password_reset_token import PasswordResetToken
from app.models.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.audit import log_event
import uuid


router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(email=user_data.email, hashed_password=hash_password(user_data.password), tenant_id=user_data.tenant_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email}


@router.post("/login")
async def login(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalars().first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token({"sub": str(user.id)})
    # create refresh token and persist
    refresh_token_str, refresh_expires = create_refresh_token()
    rt = RefreshToken(user_id=user.id, token=refresh_token_str, expires_at=refresh_expires)
    db.add(rt)
    await db.commit()
    # audit login
    await log_event(db, user.tenant_id, user.id, "user", user.id, "login", None)
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token_str}


@router.post("/refresh")
async def refresh_token(payload: dict, db: AsyncSession = Depends(get_db)):
    token = payload.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing refresh_token")
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    rt = result.scalars().first()
    if not rt or rt.revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    # issue new access token
    result_user = await db.get(User, rt.user_id)
    if not result_user:
        raise HTTPException(status_code=401, detail="Invalid token user")
    access_token = create_access_token({"sub": str(result_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password")
async def forgot_password(payload: dict, db: AsyncSession = Depends(get_db)):
    email = payload.get("email")
    # generic response regardless of whether email exists
    generic = {"ok": True, "message": "If an account with that email exists, a reset link has been generated."}
    if not email:
        return generic
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return generic
    # create token
    token = uuid.uuid4().hex
    expires = datetime.utcnow() + timedelta(hours=1)
    pr = PasswordResetToken(user_id=user.id, token=token, expires_at=expires)
    db.add(pr)
    await db.commit()
    # For now: return a message with token only in dev/testing. In production, this would be emailed.
    return {"ok": True, "message": "Password reset generated.", "debug_token": token}


@router.post("/reset-password")
async def reset_password(payload: dict, db: AsyncSession = Depends(get_db)):
    token = payload.get("token")
    new_password = payload.get("new_password")
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Missing token or new_password")
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == token))
    pr = result.scalars().first()
    if not pr or pr.used:
        raise HTTPException(status_code=400, detail="Invalid token")
    if pr.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")
    user = await db.get(User, pr.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.hashed_password = hash_password(new_password)
    pr.used = True
    db.add(user)
    db.add(pr)
    await db.commit()
    await log_event(db, user.tenant_id, user.id, "user", user.id, "password_reset", None)
    return {"ok": True}
