"""
routers/auth.py - Registration, login, and profile endpoints.
Uses async db helpers and JWT from app.auth. No ORM dependencies.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from pydantic import BaseModel, EmailStr

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    CurrentUser,
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    hashed = get_password_hash(payload.password)
    try:
        user = await create_user(email=payload.email, password_hash=hashed)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )
    return UserOut(id=user["id"], email=user["email"], role=user["role"])


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": str(user["id"]), "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserOut(id=user["id"], email=user["email"], role=user["role"]),
    )


# Alias /login -> /token for convenience
@router.post("/login", response_model=Token, include_in_schema=False)
async def login_alias(form_data: OAuth2PasswordRequestForm = Depends()):
    return await login(form_data)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser):
    return UserOut(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
    )


@router.post("/logout")
async def logout():
    # JWT is stateless; client discards the token.
    return {"message": "Logged out successfully."}
