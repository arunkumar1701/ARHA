from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from .crypto import crypto_box
from .database import get_db
from .models import Application, Notification, PublicOpportunity, Resume, User


async def _session():
    async for session in get_db():
        yield session


def _as_dict(model: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: getattr(model, field) for field in fields}


async def create_user(email: str, password_hash: str, role: str = "user") -> dict[str, Any]:
    async for session in _session():
        existing = await session.scalar(select(User).where(User.email == email.lower()))
        if existing:
            raise ValueError("Email already registered.")
        user = User(email=email.lower(), password_hash=password_hash, role=role)
        session.add(user)
        await session.flush()
        return _as_dict(user, ("id", "email", "role", "created_at"))
    raise RuntimeError("Database session unavailable.")


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    async for session in _session():
        user = await session.scalar(select(User).where(User.email == email.lower()))
        if not user:
            return None
        return _as_dict(user, ("id", "email", "password_hash", "role", "created_at"))
    return None


async def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    async for session in _session():
        user = await session.get(User, user_id)
        if not user or not user.is_active:
            return None
        return _as_dict(user, ("id", "email", "role", "created_at"))
    return None


async def save_resume(
    user_id: int, filename: str, content: str, ats_score: float | None = None
) -> int:
    async for session in _session():
        resume = Resume(
            user_id=user_id,
            filename=filename,
            content_enc=crypto_box.encrypt(content),
            ats_score=ats_score,
        )
        session.add(resume)
        await session.flush()
        return resume.id
    raise RuntimeError("Database session unavailable.")


async def get_resume(user_id: int, resume_id: int) -> dict[str, Any] | None:
    async for session in _session():
        resume = await session.scalar(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        if not resume:
            return None
        data = _as_dict(resume, ("id", "filename", "ats_score", "uploaded_at"))
        data["content"] = crypto_box.decrypt(resume.content_enc)
        return data
    return None


async def create_application(
    user_id: int,
    job_id: str,
    job_title: str,
    company: str,
    match_score: float | None = None,
) -> dict[str, Any]:
    async for session in _session():
        application = Application(
            user_id=user_id,
            job_id=job_id,
            job_title=job_title,
            company=company,
            match_score=match_score,
        )
        session.add(application)
        await session.flush()
        return _as_dict(application, ("id", "status", "applied_at"))
    raise RuntimeError("Database session unavailable.")


async def approve_application(application_id: int, approver_id: int) -> bool:
    async for session in _session():
        result = await session.execute(
            update(Application)
            .where(Application.id == application_id, Application.status == "pending")
            .values(
                status="approved",
                approved_by=approver_id,
                approved_at=datetime.now(timezone.utc),
            )
        )
        return bool(result.rowcount)
    return False


async def get_user_applications(user_id: int) -> list[dict[str, Any]]:
    async for session in _session():
        rows = (
            await session.scalars(
                select(Application)
                .where(Application.user_id == user_id)
                .order_by(Application.applied_at.desc())
            )
        ).all()
        fields = (
            "id",
            "job_id",
            "job_title",
            "company",
            "status",
            "match_score",
            "applied_at",
        )
        return [_as_dict(row, fields) for row in rows]
    return []


async def upsert_opportunity(opp: dict[str, Any]) -> None:
    async for session in _session():
        statement = insert(PublicOpportunity).values(
            source=opp["source"],
            external_id=opp["external_id"],
            title=opp["title"],
            company=opp.get("company"),
            location=opp.get("location"),
            apply_url=opp.get("apply_url"),
            tags=opp.get("tags", []),
            verified=opp.get("verified", False),
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_opportunity_source_external",
            set_={
                "title": statement.excluded.title,
                "company": statement.excluded.company,
                "location": statement.excluded.location,
                "apply_url": statement.excluded.apply_url,
                "tags": statement.excluded.tags,
                "verified": statement.excluded.verified,
                "discovered_at": datetime.now(timezone.utc),
            },
        )
        await session.execute(statement)
        return


async def get_opportunities(
    limit: int = 50, verified_only: bool = False
) -> list[dict[str, Any]]:
    async for session in _session():
        query = select(PublicOpportunity)
        if verified_only:
            query = query.where(PublicOpportunity.verified.is_(True))
        rows = (
            await session.scalars(
                query.order_by(PublicOpportunity.discovered_at.desc()).limit(limit)
            )
        ).all()
        fields = (
            "id",
            "source",
            "title",
            "company",
            "location",
            "apply_url",
            "tags",
            "verified",
            "discovered_at",
        )
        return [_as_dict(row, fields) for row in rows]
    return []


async def create_notification(user_id: int, message: str) -> None:
    async for session in _session():
        session.add(Notification(user_id=user_id, message=message))
        return


async def get_unread_notifications(user_id: int) -> list[dict[str, Any]]:
    async for session in _session():
        rows = (
            await session.scalars(
                select(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
                .order_by(Notification.created_at.desc())
            )
        ).all()
        for row in rows:
            row.is_read = True
        return [
            _as_dict(row, ("id", "message", "created_at"))
            for row in rows
        ]
    return []
