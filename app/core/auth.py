from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Resolve the current user and ensure token claims match DB state."""
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_tenant_id = payload.get("tenant_id")
        token_role = payload.get("role")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception

    # Validate tenant/role consistency to prevent cross-tenant token misuse
    if token_tenant_id is not None and user.tenant_id != token_tenant_id:
        raise credentials_exception
    if token_role is not None and user.role != token_role:
        raise credentials_exception

    return user


def require_role(*allowed_roles: str):
    """Dependency factory that ensures the current_user has one of the allowed roles.

    Usage: current_user = Depends(require_role('owner','admin'))
    """

    async def _require(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return current_user

    return _require
