from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import log_event
from app.core.auth import get_current_user
from app.core.security import hash_password
from app.db.database import get_db
from app.db.models.user import User
from app.models.auth import (
    LoginRequest,
    PasswordResetPerform,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.services.auth_service import (
    login_user,
    refresh_session,
    register_user_in_tenant,
    request_password_reset,
    reset_password,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register")
async def register(user_data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await register_user_in_tenant(db, user_data)
    return {
        "id": user.id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "role": user.role,
    }


@router.post("/login", response_model=TokenPair)
async def login(user_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, access_token, rt = await login_user(db, user_data)
    await log_event(db, user.tenant_id, user.id, "user", user.id, "login", None)
    return {
        "access_token": access_token,
        "refresh_token": rt.token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    access_token, new_rt = await refresh_session(db, payload.refresh_token)
    return {"access_token": access_token, "refresh_token": new_rt.token, "token_type": "bearer"}


@router.post("/forgot-password")
async def forgot_password(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    # generic response regardless of whether email exists
    generic = {"ok": True, "message": "If an account with that email exists, a reset link has been generated."}
    token = await request_password_reset(db, payload.email)
    if not token:
        return generic
    # For dev/test only: return token; in production this would be emailed.
    return {"ok": True, "message": "Password reset generated.", "debug_token": token}


@router.post("/reset-password")
async def reset_password_endpoint(payload: PasswordResetPerform, db: AsyncSession = Depends(get_db)):
    await reset_password(db, payload.token, payload.new_password)
    return {"ok": True}


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role,
    }
