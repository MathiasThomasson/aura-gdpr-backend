from dataclasses import dataclass

from fastapi import Depends

from app.core.auth import get_current_user
from app.db.models.user import User


@dataclass
class CurrentContext:
    user: User
    tenant_id: int
    role: str


async def current_context(current_user: User = Depends(get_current_user)) -> CurrentContext:
    return CurrentContext(user=current_user, tenant_id=current_user.tenant_id, role=current_user.role)
