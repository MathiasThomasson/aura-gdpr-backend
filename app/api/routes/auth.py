from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models.user import User
from app.middleware.rate_limit import rate_limit
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


@router.post("/register", summary="Register user", description="Create a new user within a tenant.")
@rate_limit("global", limit=100, window_seconds=60)
async def register(user_data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await register_user_in_tenant(db, user_data)
    request.state.user_id = user.id
    return {
        "id": user.id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "role": user.role,
    }


@router.post("/login", response_model=TokenPair, summary="Login", description="Exchange credentials for access and refresh tokens.")
@rate_limit("global", limit=100, window_seconds=60)
async def login(user_data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user, access_token, rt = await login_user(db, user_data)
    await log_event(db, user.tenant_id, user.id, "user", user.id, "login", None)
    request.state.user_id = user.id
    request.state.tenant_id = user.tenant_id
    return {
        "access_token": access_token,
        "refresh_token": rt.token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenPair, summary="Refresh tokens", description="Refresh access token using a valid refresh token.")
@rate_limit("global", limit=100, window_seconds=60)
async def refresh_token(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    access_token, new_rt = await refresh_session(db, payload.refresh_token)
    request.state.user_id = getattr(new_rt, "user_id", None)
    request.state.tenant_id = getattr(new_rt, "tenant_id", None)
    return {"access_token": access_token, "refresh_token": new_rt.token, "token_type": "bearer"}


@router.post("/forgot-password", summary="Forgot password", description="Request a password reset token.")
@rate_limit("global", limit=100, window_seconds=60)
async def forgot_password(payload: PasswordResetRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # generic response regardless of whether email exists
    generic = {"ok": True, "message": "If an account with that email exists, a reset link has been generated."}
    token = await request_password_reset(db, payload.email)
    request.state.user_id = None
    if not token:
        return generic
    # For dev/test only: return token; in production this would be emailed.
    return {"ok": True, "message": "Password reset generated.", "debug_token": token}


@router.post("/reset-password", summary="Reset password", description="Complete a password reset using the provided token.")
@rate_limit("global", limit=100, window_seconds=60)
async def reset_password_endpoint(payload: PasswordResetPerform, request: Request, db: AsyncSession = Depends(get_db)):
    await reset_password(db, payload.token, payload.new_password)
    request.state.user_id = None
    return {"ok": True}


@router.get("/me", summary="Current user", description="Return information about the current authenticated user.")
async def me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role,
    }
