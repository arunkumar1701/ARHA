from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def configure_database(url: str | None = None) -> None:
    global engine, session_factory
    database_url = normalize_database_url(url or settings.database_url)
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=settings.environment == "development",
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_database() -> None:
    if engine is None:
        configure_database()
    assert engine is not None
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_database() -> None:
    global engine, session_factory
    if engine is not None:
        await engine.dispose()
    engine = None
    session_factory = None


async def database_is_healthy() -> bool:
    try:
        if engine is None:
            return False
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if session_factory is None:
        raise RuntimeError("Database is not initialized.")
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
