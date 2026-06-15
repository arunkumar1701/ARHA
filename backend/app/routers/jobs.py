"""
routers/jobs.py - Job search, public opportunities, and application endpoints.
All real-time data; no ORM, no mock responses.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.auth import CurrentUser, AdminUser
from app.db import (
    create_application,
    approve_application,
    get_user_applications,
    get_opportunities,
)
from app.agents.job_search_agent import JobSearchAgent
from app.agents.matching_agent import JobMatchingAgent

router = APIRouter(prefix="/jobs", tags=["jobs"])

_search_agent = JobSearchAgent()
_match_agent = JobMatchingAgent()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: bool = True


class ApplicationRequest(BaseModel):
    job_id: str
    job_title: str
    company: str
    resume_text: str
    job_description: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/search")
async def search_jobs(
    q: str = Query(..., description="Job title, skill, or keyword"),
    location: Optional[str] = Query(None),
    remote: bool = Query(True),
    page: int = Query(1, ge=1),
) -> dict[str, Any]:
    """Live job search via JobSearchAgent (Jobicy / Remotive / Arbeitnow)."""
    results = await _search_agent.search(
        query=q,
        location=location,
        remote=remote,
        page=page,
    )
    return results


@router.get("/opportunities")
async def list_opportunities(
    limit: int = Query(50, ge=1, le=200),
    verified_only: bool = Query(False),
) -> list[dict[str, Any]]:
    """Return publicly discovered opportunities from the PostgreSQL cache."""
    return await get_opportunities(limit=limit, verified_only=verified_only)


@router.post("/match")
async def match_job(
    resume_text: str,
    job_description: str,
    current_user: CurrentUser = None,  # optional auth
) -> dict[str, Any]:
    """Score a resume against a job description using JobMatchingAgent."""
    job_data = {
        "title": "Job",
        "company": "Company",
        "location": "Location",
        "employment_type": "Full-time",
        "requirements": job_description,
    }
    result = await _match_agent.score(resume_text=resume_text, job=job_data)
    return result


@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_for_job(
    payload: ApplicationRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Create a job application (status='pending', requires admin approval).
    Never auto-applies. The user must explicitly trigger this endpoint.
    """
    job_data = {
        "title": payload.job_title,
        "company": payload.company,
        "location": "Location",
        "employment_type": "Full-time",
        "requirements": payload.job_description,
    }
    match = await _match_agent.score(
        resume_text=payload.resume_text,
        job=job_data,
    )
    match_score = match.get("overall_score", 0.0)

    application = await create_application(
        user_id=current_user["id"],
        job_id=payload.job_id,
        job_title=payload.job_title,
        company=payload.company,
        match_score=match_score,
    )
    return {
        "application_id": application["id"],
        "status": application["status"],
        "match_score": match_score,
        "message": "Application submitted for review. Approval required before submission to employer.",
    }


@router.get("/applications")
async def list_applications(current_user: CurrentUser) -> list[dict[str, Any]]:
    """List the current user's job applications."""
    return await get_user_applications(current_user["id"])


@router.post("/applications/{application_id}/approve")
async def approve(
    application_id: int,
    admin: AdminUser,
) -> dict[str, Any]:
    """Admin-only: approve a pending application."""
    ok = await approve_application(application_id=application_id, approver_id=admin["id"])
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or already processed.",
        )
    return {"application_id": application_id, "status": "approved"}
