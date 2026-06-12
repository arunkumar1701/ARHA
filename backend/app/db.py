"""
db.py - Async PostgreSQL database layer using SQLAlchemy 2.x + asyncpg.
All user-sensitive fields are encrypted at rest via crypto.py.
No SQLite, no local file storage.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings
from .crypto import crypto_box

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine (module-level singleton, initialised in app lifespan)
# ---------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Call init_db() first.")
    return _session_factory


async def init_db() -> None:
    """Create the async engine, run schema migrations, and warm the pool."""
    global _engine, _session_factory

    database_url = settings.DATABASE_URL
    # SQLAlchemy requires the asyncpg dialect prefix
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    _engine = create_async_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await _create_tables(conn)

    logger.info("Database initialised (PostgreSQL / asyncpg).")


async def close_db() -> None:
    """Dispose the connection pool on shutdown."""
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connection pool disposed.")


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session; roll back on error, commit on success."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
async def _create_tables(conn: AsyncConnection) -> None:
    """Idempotent DDL — safe to run on every startup."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            email       TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS resumes (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename    TEXT NOT NULL,
            content_enc TEXT NOT NULL,
            ats_score   REAL,
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS applications (
            id              SERIAL PRIMARY KEY,
            user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_id          TEXT NOT NULL,
            job_title       TEXT,
            company         TEXT,
            status          TEXT NOT NULL DEFAULT 'pending',
            match_score     REAL,
            applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            approved_by     INTEGER REFERENCES users(id),
            approved_at     TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS public_opportunities (
            id          SERIAL PRIMARY KEY,
            source      TEXT NOT NULL,
            external_id TEXT NOT NULL,
            title       TEXT NOT NULL,
            company     TEXT,
            location    TEXT,
            apply_url   TEXT,
            tags        JSONB,
            verified    BOOLEAN NOT NULL DEFAULT FALSE,
            discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(source, external_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message     TEXT NOT NULL,
            read        BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
    ]
    for stmt in statements:
        await conn.execute(text(stmt))


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------
async def create_user(email: str, password_hash: str, role: str = "user") -> dict[str, Any]:
    async with get_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO users (email, password_hash, role) "
                "VALUES (:email, :password_hash, :role) "
                "ON CONFLICT (email) DO NOTHING "
                "RETURNING id, email, role, created_at"
            ),
            {"email": email, "password_hash": password_hash, "role": role},
        )
        row = result.fetchone()
        if row is None:
            raise ValueError("Email already registered.")
        return dict(row._mapping)


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    async with get_session() as session:
        result = await session.execute(
            text("SELECT id, email, password_hash, role, created_at FROM users WHERE email = :email"),
            {"email": email},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    async with get_session() as session:
        result = await session.execute(
            text("SELECT id, email, role, created_at FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


# ---------------------------------------------------------------------------
# Resume helpers
# ---------------------------------------------------------------------------
async def save_resume(
    user_id: int, filename: str, content: str, ats_score: float | None = None
) -> int:
    """Encrypt and persist resume text. Returns the new row id."""
    encrypted = crypto_box.encrypt(content)
    async with get_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO resumes (user_id, filename, content_enc, ats_score) "
                "VALUES (:uid, :fname, :enc, :score) RETURNING id"
            ),
            {"uid": user_id, "fname": filename, "enc": encrypted, "score": ats_score},
        )
        return result.scalar_one()


async def get_resume(user_id: int, resume_id: int) -> dict[str, Any] | None:
    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, filename, content_enc, ats_score, uploaded_at "
                "FROM resumes WHERE id = :rid AND user_id = :uid"
            ),
            {"rid": resume_id, "uid": user_id},
        )
        row = result.fetchone()
        if row is None:
            return None
        data = dict(row._mapping)
        data["content"] = crypto_box.decrypt(data.pop("content_enc"))
        return data


# ---------------------------------------------------------------------------
# Application helpers
# ---------------------------------------------------------------------------
async def create_application(
    user_id: int,
    job_id: str,
    job_title: str,
    company: str,
    match_score: float | None = None,
) -> dict[str, Any]:
    async with get_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO applications "
                "(user_id, job_id, job_title, company, match_score) "
                "VALUES (:uid, :jid, :title, :company, :score) "
                "RETURNING id, status, applied_at"
            ),
            {
                "uid": user_id,
                "jid": job_id,
                "title": job_title,
                "company": company,
                "score": match_score,
            },
        )
        return dict(result.fetchone()._mapping)


async def approve_application(application_id: int, approver_id: int) -> bool:
    async with get_session() as session:
        result = await session.execute(
            text(
                "UPDATE applications SET status='approved', approved_by=:approver, "
                "approved_at=NOW() WHERE id=:aid AND status='pending' RETURNING id"
            ),
            {"approver": approver_id, "aid": application_id},
        )
        return result.fetchone() is not None


async def get_user_applications(user_id: int) -> list[dict[str, Any]]:
    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, job_id, job_title, company, status, match_score, applied_at "
                "FROM applications WHERE user_id = :uid ORDER BY applied_at DESC"
            ),
            {"uid": user_id},
        )
        return [dict(row._mapping) for row in result.fetchall()]


# ---------------------------------------------------------------------------
# Public opportunity helpers
# ---------------------------------------------------------------------------
async def upsert_opportunity(opp: dict[str, Any]) -> None:
    async with get_session() as session:
        await session.execute(
            text(
                "INSERT INTO public_opportunities "
                "(source, external_id, title, company, location, apply_url, tags, verified) "
                "VALUES (:source, :ext_id, :title, :company, :location, :url, :tags::jsonb, :verified) "
                "ON CONFLICT (source, external_id) DO UPDATE SET "
                "title=EXCLUDED.title, company=EXCLUDED.company, "
                "location=EXCLUDED.location, apply_url=EXCLUDED.apply_url, "
                "tags=EXCLUDED.tags, verified=EXCLUDED.verified, "
                "discovered_at=NOW()"
            ),
            {
                "source": opp["source"],
                "ext_id": opp["external_id"],
                "title": opp["title"],
                "company": opp.get("company"),
                "location": opp.get("location"),
                "url": opp.get("apply_url"),
                "tags": __import__("json").dumps(opp.get("tags", [])),
                "verified": opp.get("verified", False),
            },
        )


async def get_opportunities(
    limit: int = 50, verified_only: bool = False
) -> list[dict[str, Any]]:
    async with get_session() as session:
        where = "WHERE verified = TRUE" if verified_only else ""
        result = await session.execute(
            text(
                f"SELECT id, source, title, company, location, apply_url, tags, verified, discovered_at "
                f"FROM public_opportunities {where} ORDER BY discovered_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in result.fetchall()]


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------
async def create_notification(user_id: int, message: str) -> None:
    async with get_session() as session:
        await session.execute(
            text(
                "INSERT INTO notifications (user_id, message) VALUES (:uid, :msg)"
            ),
            {"uid": user_id, "msg": message},
        )


async def get_unread_notifications(user_id: int) -> list[dict[str, Any]]:
    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, message, created_at FROM notifications "
                "WHERE user_id = :uid AND read = FALSE ORDER BY created_at DESC"
            ),
            {"uid": user_id},
        )
        rows = result.fetchall()
        if rows:
            ids = [r.id for r in rows]
            await session.execute(
                text("UPDATE notifications SET read=TRUE WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
        return [dict(row._mapping) for row in rows]
