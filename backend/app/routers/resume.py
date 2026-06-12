import io
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Resume
from app.auth import get_current_user
from app.agents.resume_agent import ResumeAgent

router = APIRouter(prefix="/resume", tags=["resume"])

_resume_agent = ResumeAgent()


class ResumeAnalysisResponse(BaseModel):
    id: int
    filename: str
    ats_score: Optional[float]
    skills: Optional[list]
    experience_years: Optional[float]
    suggestions: Optional[list]
    created_at: str

    class Config:
        from_attributes = True


class OptimizeRequest(BaseModel):
    job_description: str
    resume_id: Optional[int] = None


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload PDF or DOCX resume, extract text, run ATS scoring."""
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are accepted",
        )
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5 MB limit
        raise HTTPException(status_code=400, detail="File size must be under 5 MB")

    # Extract text and analyse
    analysis = await _resume_agent.analyse(
        file_bytes=content,
        filename=file.filename,
        content_type=file.content_type,
    )

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        raw_text=analysis.get("raw_text", ""),
        ats_score=analysis.get("ats_score"),
        skills=json.dumps(analysis.get("skills", [])),
        experience_years=analysis.get("experience_years"),
        suggestions=json.dumps(analysis.get("suggestions", [])),
        file_data=content,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return {
        "id": resume.id,
        "filename": resume.filename,
        "ats_score": resume.ats_score,
        "skills": json.loads(resume.skills) if resume.skills else [],
        "experience_years": resume.experience_years,
        "suggestions": json.loads(resume.suggestions) if resume.suggestions else [],
        "created_at": resume.created_at.isoformat(),
    }


@router.get("/")
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(desc(Resume.created_at))
    )
    resumes = result.scalars().all()
    return {
        "resumes": [
            {
                "id": r.id,
                "filename": r.filename,
                "ats_score": r.ats_score,
                "skills": json.loads(r.skills) if r.skills else [],
                "experience_years": r.experience_years,
                "suggestions": json.loads(r.suggestions) if r.suggestions else [],
                "created_at": r.created_at.isoformat(),
            }
            for r in resumes
        ]
    }


@router.post("/optimize")
async def optimize_resume(
    payload: OptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rewrite resume to better match a specific job description."""
    if payload.resume_id:
        result = await db.execute(
            select(Resume).where(
                Resume.id == payload.resume_id,
                Resume.user_id == current_user.id,
            )
        )
        resume = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Resume)
            .where(Resume.user_id == current_user.id)
            .order_by(desc(Resume.created_at))
            .limit(1)
        )
        resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="No resume found. Please upload one first.")

    optimized = await _resume_agent.optimize(
        resume_text=resume.raw_text,
        job_description=payload.job_description,
    )
    return {
        "original_ats_score": resume.ats_score,
        "optimized_resume": optimized.get("optimized_text"),
        "new_ats_score": optimized.get("new_ats_score"),
        "changes_made": optimized.get("changes", []),
    }


@router.get("/{resume_id}")
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {
        "id": resume.id,
        "filename": resume.filename,
        "ats_score": resume.ats_score,
        "skills": json.loads(resume.skills) if resume.skills else [],
        "experience_years": resume.experience_years,
        "raw_text": resume.raw_text,
        "suggestions": json.loads(resume.suggestions) if resume.suggestions else [],
        "created_at": resume.created_at.isoformat(),
    }


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    await db.delete(resume)
    await db.commit()
    return {"message": "Resume deleted"}
