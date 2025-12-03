from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Dict

from jose import jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.config import settings

# Use pbkdf2 to avoid bcrypt backend quirks on some platforms while keeping strong hashing.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        # Unsupported or legacy hash scheme; treat as invalid password
        return False
    except Exception:
        # Unexpected errors must not leak; fail closed
        return False


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT with provided claims (expects sub, tenant_id, role)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(expires_delta: timedelta | None = None) -> tuple[str, datetime]:
    """Return (token_string, expires_at)"""
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    # return naive UTC to align with existing comparisons/tests
    return token, expires.replace(tzinfo=None)
