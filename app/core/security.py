from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Switched from bcrypt -> pbkdf2_sha256 to avoid local bcrypt backend issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _make_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    data = {"sub": subject, "type": "access", **(extra or {})}
    return _make_token(data, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(subject: str) -> str:
    data = {"sub": subject, "type": "refresh"}
    return _make_token(data, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict[str, Any]:
    """Raises JWTError on invalid/expired token."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])