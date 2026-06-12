"""
auth.py - JWT authentication, password hashing, and RBAC.
Uses the async db.py helpers; no ORM session dependency injection.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings
from .db import get_user_by_email, get_user_by_id

# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES


class TokenData(BaseModel):
    sub: str  # user id as string
    role: str = "user"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(plain: str) -> str:
    return pwd_context.hash(plain)


# keep old alias for compatibility
hash_password = get_password_hash


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT and return the payload, raising HTTPException on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, Any]:
    """FastAPI dependency: decode JWT and load user from PostgreSQL."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise credentials_exception
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    return current_user


async def require_admin(
    current_user: Annotated[dict, Depends(get_current_active_user)],
) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[dict, Depends(get_current_active_user)]
AdminUser = Annotated[dict, Depends(require_admin)]
