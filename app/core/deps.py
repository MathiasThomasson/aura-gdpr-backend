from dataclasses import dataclass

from fastapi import Depends, Request

from app.core.auth import get_current_user
from app.db.models.user import User


@dataclass
class CurrentContext:
    user: User
    tenant_id: int
    role: str


async def current_context(request: Request, current_user: User = Depends(get_current_user)) -> CurrentContext:
    request.state.tenant_id = current_user.tenant_id
    request.state.role = current_user.role
    return CurrentContext(user=current_user, tenant_id=current_user.tenant_id, role=current_user.role)
