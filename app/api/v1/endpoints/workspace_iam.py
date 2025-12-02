import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.security import hash_password
from app.db.database import get_db
from app.db.models.user import User
from app.db.models.user_tenant import UserTenant
from app.schemas.workspace_iam import (
    WorkspaceUserInviteRequest,
    WorkspaceUserListItem,
    WorkspaceUserUpdateRequest,
)

router = APIRouter(prefix="/api/admin/workspace/users", tags=["Workspace Admin"])


async def _current_membership(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> UserTenant:
    res = await db.execute(
        select(UserTenant).where(UserTenant.user_id == current_user.id, UserTenant.tenant_id == current_user.tenant_id)
    )
    membership = res.scalars().first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership not found")
    return membership


async def _require_workspace_admin(membership: UserTenant = Depends(_current_membership)) -> UserTenant:
    if membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
    return membership


def _to_response(user_tenant: UserTenant, user: User) -> WorkspaceUserListItem:
    return WorkspaceUserListItem(
        id=user_tenant.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user_tenant.role,
        status="active" if user_tenant.is_active else "disabled",
        last_login=getattr(user, "last_login_at", None),
    )


@router.get("", response_model=list[WorkspaceUserListItem])
async def list_workspace_users(
    membership: UserTenant = Depends(_require_workspace_admin), db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(UserTenant, User)
        .join(User, User.id == UserTenant.user_id)
        .where(UserTenant.tenant_id == membership.tenant_id)
    )
    rows = res.all()
    return [_to_response(ut, user) for ut, user in rows]


@router.post("/invite", response_model=WorkspaceUserListItem, status_code=status.HTTP_201_CREATED)
async def invite_workspace_user(
    payload: WorkspaceUserInviteRequest,
    membership: UserTenant = Depends(_require_workspace_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = membership.tenant_id

    user_res = await db.execute(select(User).where(User.email == payload.email))
    user = user_res.scalars().first()
    if not user:
        user = User(
            email=payload.email,
            full_name=None,
            tenant_id=tenant_id,
            hashed_password=hash_password(secrets.token_hex(12)),
            role=payload.role,
            is_active=True,
            status="active",
        )
        db.add(user)
        await db.flush()

    ut_res = await db.execute(
        select(UserTenant).where(UserTenant.user_id == user.id, UserTenant.tenant_id == tenant_id)
    )
    user_tenant = ut_res.scalars().first()
    if user_tenant:
        user_tenant.role = payload.role
        user_tenant.is_active = True
    else:
        user_tenant = UserTenant(user_id=user.id, tenant_id=tenant_id, role=payload.role, is_active=True)
        db.add(user_tenant)

    await db.commit()
    await db.refresh(user)
    await db.refresh(user_tenant)
    return _to_response(user_tenant, user)


@router.patch("/{user_tenant_id}", response_model=WorkspaceUserListItem)
async def update_workspace_user(
    user_tenant_id: int,
    payload: WorkspaceUserUpdateRequest,
    membership: UserTenant = Depends(_require_workspace_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(UserTenant, User)
        .join(User, User.id == UserTenant.user_id)
        .where(UserTenant.id == user_tenant_id, UserTenant.tenant_id == membership.tenant_id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in workspace")
    target_ut, target_user = row

    if payload.role and payload.role != target_ut.role:
        owners_res = await db.execute(
            select(func.count()).select_from(UserTenant).where(
                UserTenant.tenant_id == membership.tenant_id, UserTenant.role == "owner"
            )
        )
        if target_ut.role == "owner" and payload.role != "owner" and owners_res.scalar_one() <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote the last remaining owner")
        target_ut.role = payload.role

    if payload.status:
        if payload.status == "active":
            target_ut.is_active = True
        elif payload.status == "disabled":
            target_ut.is_active = False
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    db.add(target_ut)
    await db.commit()
    await db.refresh(target_ut)
    await db.refresh(target_user)
    return _to_response(target_ut, target_user)
