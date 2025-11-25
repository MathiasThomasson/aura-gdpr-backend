from fastapi import Depends, HTTPException
from jose import JWTError, jwt
from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if user is None:
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
