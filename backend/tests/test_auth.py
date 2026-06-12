import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "email": "newuser@arha.dev",
            "password": "SecurePass99!",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@arha.dev"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    payload = {
        "email": "dup@arha.dev",
        "password": "SecurePass99!",
        "full_name": "Dup User",
    }
    await client.post("/auth/register", json=payload)
    resp2 = await client.post("/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "email": "logintest@arha.dev",
            "password": "LoginPass99!",
            "full_name": "Login User",
        },
    )
    response = await client.post(
        "/auth/login",
        data={"username": "logintest@arha.dev", "password": "LoginPass99!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "email": "wrongpw@arha.dev",
            "password": "CorrectPass99!",
            "full_name": "WrongPW",
        },
    )
    resp = await client.post(
        "/auth/login",
        data={"username": "wrongpw@arha.dev", "password": "WrongPass!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, auth_headers: dict):
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
