"""
conftest.py - pytest fixtures for ARHA backend tests.
All db calls are patched with AsyncMock so tests run without a real database.
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

# Point to a dummy DB URL so config doesn't fail
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("ARHA_PASSPHRASE", "test-passphrase-for-ci-only")

from app.main import app  # noqa: E402  (import after env setup)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture()
async def client():
    """
    HTTPX async test client with all db calls patched out.
    Tests exercise routing, serialisation, and auth logic
    without requiring a real PostgreSQL instance.
    """
    with (
        patch("app.db.init_db", new_callable=AsyncMock),
        patch("app.db.close_db", new_callable=AsyncMock),
        patch("app.db.create_user", new_callable=AsyncMock) as mock_create_user,
        patch("app.db.get_user_by_email", new_callable=AsyncMock) as mock_get_email,
        patch("app.db.get_user_by_id", new_callable=AsyncMock) as mock_get_id,
        patch("app.db.save_resume", new_callable=AsyncMock),
        patch("app.db.get_resume", new_callable=AsyncMock),
        patch("app.db.create_application", new_callable=AsyncMock),
        patch("app.db.get_user_applications", new_callable=AsyncMock) as mock_apps,
        patch("app.db.get_opportunities", new_callable=AsyncMock) as mock_opps,
    ):
        # Provide sensible default returns
        mock_create_user.return_value = {"id": 1, "email": "test@example.com", "role": "user"}
        mock_get_email.return_value = None  # default: user not found (register will create)
        mock_get_id.return_value = {"id": 1, "email": "test@example.com", "role": "user"}
        mock_apps.return_value = []
        mock_opps.return_value = []

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


@pytest_asyncio.fixture()
async def auth_headers(client: AsyncClient):
    """Return Authorization headers for a registered + logged-in test user."""
    from app.auth import get_password_hash, create_access_token
    from datetime import timedelta

    with patch(
        "app.db.get_user_by_email",
        new_callable=AsyncMock,
        return_value={
            "id": 1,
            "email": "test@example.com",
            "role": "user",
            "password_hash": get_password_hash("testpassword"),
        },
    ):
        token = create_access_token(
            {"sub": "1", "role": "user"}, expires_delta=timedelta(minutes=60)
        )
        return {"Authorization": f"Bearer {token}"}
