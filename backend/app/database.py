# backend/app/database.py
# Async PostgreSQL engine via SQLAlchemy 2.0 + asyncpg
# Replaces SQLite — supports connection pooling and concurrent requests
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.arha_env == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,           # recycle stale connections automatically
    pool_recycle=1800,            # recycle every 30 min for serverless DBs
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all tables on startup (Alembic handles production migrations)."""
    async with engine.begin() as conn:
        from . import models  # noqa: F401  — import to register all ORM models
        await conn.run_sync(Base.metadata.create_all)
