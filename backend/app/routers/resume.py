"""
routers/resume.py - Resume upload, ATS analysis, optimization, and retrieval.
Uses async db helpers; no ORM. PDF and DOCX extraction via app.resume module.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from app.auth import CurrentUser
from app.db import save_resume, get_resume
from app.resume import extract_text_from_bytes
from app.resume import analyze_resume
from app.optimizer import optimize_resume_with_llm, generate_keyword_suggestions
from app.agents.resume_agent import ResumeAgent

router = APIRouter(prefix="/resume", tags=["resume"])
_resume_agent = ResumeAgent()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class OptimizeRequest(BaseModel):
    resume_id: int
    job_description: str
    job_title: Optional[str] = ""
    company: Optional[str] = ""


class KeywordRequest(BaseModel):
    resume_text: str
    job_description: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
) -> dict[str, Any]:
    """
    Accept PDF or DOCX, extract text, run ATS analysis,
    encrypt and persist to PostgreSQL.
    """
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    allowed = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX files are supported.",
        )

    raw_bytes = await file.read()
    text = extract_text_from_bytes(raw_bytes, filename=file.filename or "resume")
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the uploaded file.",
        )

    analysis = analyze_resume(text)
    ats_score = analysis.get("ats_score", 0.0)

    resume_id = await save_resume(
        user_id=current_user["id"],
        filename=file.filename or "resume",
        content=text,
        ats_score=ats_score,
    )
    return {
        "resume_id": resume_id,
        "filename": file.filename,
        "ats_score": ats_score,
        "word_count": analysis.get("word_count"),
        "ats_flags": analysis.get("ats_flags", []),
        "education_keywords": analysis.get("education_keywords", []),
        "experience_keywords": analysis.get("experience_keywords", []),
    }


@router.get("/{resume_id}")
async def get_resume_detail(
    resume_id: int,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Retrieve and decrypt a stored resume. Only accessible by the owner."""
    record = await get_resume(user_id=current_user["id"], resume_id=resume_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return {
        "resume_id": record["id"],
        "filename": record["filename"],
        "ats_score": record["ats_score"],
        "uploaded_at": record["uploaded_at"],
        "text_preview": record["content"][:500],
    }


@router.post("/analyze")
async def analyze(
    resume_id: int,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Run full ATS analysis on a stored resume."""
    record = await get_resume(user_id=current_user["id"], resume_id=resume_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return analyze_resume(record["content"])


@router.post("/optimize")
async def optimize(
    payload: OptimizeRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """GPT-4 powered resume optimization against a job description."""
    record = await get_resume(user_id=current_user["id"], resume_id=payload.resume_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return await optimize_resume_with_llm(
        resume_text=record["content"],
        job_description=payload.job_description,
        job_title=payload.job_title or "",
        company=payload.company or "",
    )


@router.post("/keywords")
async def keywords(payload: KeywordRequest) -> dict[str, Any]:
    """Lightweight keyword gap analysis (no LLM required)."""
    return generate_keyword_suggestions(
        resume_text=payload.resume_text,
        job_description=payload.job_description,
    )
