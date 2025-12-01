from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.iam import IamUserRead, IamUserUpdate, InviteUserRequest
from app.services.iam_service import invite_user, list_users, patch_user, to_read_model, update_user
from app.services.email import send_templated_email

router = APIRouter(prefix="/api/iam/users", tags=["IAM"])


def _ensure_admin(ctx: CurrentContext):
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient privileges")


@router.get("", response_model=list[IamUserRead])
async def list_tenant_users(db: AsyncSession = Depends(get_db), ctx: CurrentContext = Depends(current_context)):
    _ensure_admin(ctx)
    users = await list_users(db, ctx.tenant_id)
    return [IamUserRead(**to_read_model(u)) for u in users]


@router.get("/{user_id}", response_model=IamUserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    if ctx.role not in ("owner", "admin") and ctx.user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    users = await list_users(db, ctx.tenant_id)
    target = next((u for u in users if u.id == user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return IamUserRead(**to_read_model(target))


@router.post("/invite", response_model=IamUserRead, status_code=201)
async def invite(
    payload: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    _ensure_admin(ctx)
    user = await invite_user(db, ctx.tenant_id, payload)
    await send_templated_email(
        to=user.email,
        subject="You are invited",
        template="user_invite_en.txt",
        context={
            "recipient_name": user.email,
            "organization_name": str(ctx.tenant_id),
            "link": "https://app.example.com/invite",
        },
    )
    return IamUserRead(**to_read_model(user))


@router.put("/{user_id}", response_model=IamUserRead)
async def update_user_endpoint(
    user_id: int,
    payload: IamUserUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    _ensure_admin(ctx)
    user = await update_user(db, ctx.tenant_id, user_id, payload)
    return IamUserRead(**to_read_model(user))


@router.patch("/{user_id}", response_model=IamUserRead)
async def patch_user_endpoint(
    user_id: int,
    payload: IamUserUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    _ensure_admin(ctx)
    user = await patch_user(db, ctx.tenant_id, user_id, payload)
    return IamUserRead(**to_read_model(user))
