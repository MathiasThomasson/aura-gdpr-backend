from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from datetime import datetime, timedelta
from jose import jwt


def test_password_hashing():
    pw = "super-secret"
    h = hash_password(pw)
    assert verify_password(pw, h) is True
    assert verify_password("bad", h) is False


def test_create_access_token():
    token = create_access_token({"sub": "1"})
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded.get("sub") == "1"


def test_create_refresh_token():
    token, expires = create_refresh_token()
    assert isinstance(token, str) and len(token) > 0
    assert isinstance(expires, datetime)
    assert expires > datetime.utcnow()
