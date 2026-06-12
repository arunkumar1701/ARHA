"""
test_auth.py - Tests for /auth endpoints.
All PostgreSQL calls are mocked via conftest.py fixtures.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """POST /auth/register with a new email returns 201 and the user object."""
    with patch("app.db.create_user", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {"id": 1, "email": "new@example.com", "role": "user"}
        response = await client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "SecurePass123!"},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "user"
    assert "id" in body


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """POST /auth/register with an existing email returns 409."""
    with patch("app.db.create_user", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = ValueError("Email already registered.")
        response = await client.post(
            "/auth/register",
            json={"email": "existing@example.com", "password": "SecurePass123!"},
        )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """POST /auth/token with correct credentials returns a JWT."""
    from app.auth import get_password_hash

    with patch("app.db.get_user_by_email", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "id": 1,
            "email": "test@example.com",
            "role": "user",
            "password_hash": get_password_hash("testpassword"),
        }
        response = await client.post(
            "/auth/token",
            data={"username": "test@example.com", "password": "testpassword"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """POST /auth/token with wrong password returns 401."""
    from app.auth import get_password_hash

    with patch("app.db.get_user_by_email", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "id": 1,
            "email": "test@example.com",
            "role": "user",
            "password_hash": get_password_hash("correctpassword"),
        }
        response = await client.post(
            "/auth/token",
            data={"username": "test@example.com", "password": "wrongpassword"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, auth_headers: dict):
    """GET /auth/me with a valid JWT returns the current user."""
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    """GET /auth/me without a token returns 401."""
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /health returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
