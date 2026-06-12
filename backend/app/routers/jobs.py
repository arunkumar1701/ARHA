from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import User, SavedJob, JobApplication
from app.auth import get_current_user
from app.agents.job_search_agent import JobSearchAgent
from app.agents.matching_agent import JobMatchingAgent

router = APIRouter(prefix="/jobs", tags=["jobs"])

_search_agent = JobSearchAgent()
_match_agent = JobMatchingAgent()


class JobSearchRequest(BaseModel):
    keywords: str
    location: Optional[str] = "remote"
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    limit: int = 20


class SaveJobRequest(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    url: str
    description: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    source: Optional[str] = None


class ApplicationRequest(BaseModel):
    saved_job_id: int
    cover_letter: Optional[str] = None
    resume_version: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: str  # applied, interviewing, offered, rejected, withdrawn
    notes: Optional[str] = None


@router.post("/search")
async def search_jobs(
    payload: JobSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Search real-time jobs across multiple sources."""
    results = await _search_agent.search(
        keywords=payload.keywords,
        location=payload.location,
        job_type=payload.job_type,
        experience_level=payload.experience_level,
        limit=payload.limit,
    )
    return {"jobs": results, "total": len(results)}


@router.post("/match")
async def match_jobs(
    payload: JobSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search jobs and rank by AI match score against user resume."""
    jobs = await _search_agent.search(
        keywords=payload.keywords,
        location=payload.location,
        job_type=payload.job_type,
        experience_level=payload.experience_level,
        limit=payload.limit,
    )
    if not jobs:
        return {"jobs": [], "total": 0}
    # Fetch latest resume text for user
    from app.models import Resume
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(desc(Resume.created_at))
        .limit(1)
    )
    resume = result.scalar_one_or_none()
    resume_text = resume.raw_text if resume else ""
    matched = await _match_agent.rank_jobs(jobs=jobs, resume_text=resume_text)
    return {"jobs": matched, "total": len(matched)}


@router.post("/save", status_code=status.HTTP_201_CREATED)
async def save_job(
    payload: SaveJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a job for later review — no auto-apply."""
    existing = await db.execute(
        select(SavedJob).where(
            SavedJob.user_id == current_user.id,
            SavedJob.job_id == payload.job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Job already saved")
    job = SavedJob(
        user_id=current_user.id,
        job_id=payload.job_id,
        title=payload.title,
        company=payload.company,
        location=payload.location,
        url=payload.url,
        description=payload.description,
        salary_range=payload.salary_range,
        job_type=payload.job_type,
        source=payload.source,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/saved")
async def get_saved_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob)
        .where(SavedJob.user_id == current_user.id)
        .order_by(desc(SavedJob.saved_at))
    )
    jobs = result.scalars().all()
    return {"jobs": jobs, "total": len(jobs)}


@router.delete("/saved/{job_id}")
async def remove_saved_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob).where(
            SavedJob.id == job_id,
            SavedJob.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Saved job not found")
    await db.delete(job)
    await db.commit()
    return {"message": "Job removed from saved list"}


@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    payload: ApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User explicitly applies to a saved job — requires intentional user action."""
    result = await db.execute(
        select(SavedJob).where(
            SavedJob.id == payload.saved_job_id,
            SavedJob.user_id == current_user.id,
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved job not found")
    application = JobApplication(
        user_id=current_user.id,
        saved_job_id=payload.saved_job_id,
        cover_letter=payload.cover_letter,
        resume_version=payload.resume_version,
        status="applied",
        applied_at=datetime.utcnow(),
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


@router.get("/applications")
async def get_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobApplication)
        .where(JobApplication.user_id == current_user.id)
        .order_by(desc(JobApplication.applied_at))
    )
    apps = result.scalars().all()
    return {"applications": apps, "total": len(apps)}


@router.patch("/applications/{app_id}")
async def update_application_status(
    app_id: int,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    valid_statuses = {"applied", "interviewing", "offered", "rejected", "withdrawn"}
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == app_id,
            JobApplication.user_id == current_user.id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    app.status = payload.status
    if payload.notes:
        app.notes = payload.notes
    await db.commit()
    await db.refresh(app)
    return app
