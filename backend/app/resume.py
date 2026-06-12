"""
resume.py - Production-grade resume text extraction and analysis utilities.

Supports:
  - PDF extraction via pypdf
  - DOCX extraction via python-docx
  - Bytes-based input (no temp files needed)
  - Structured analysis with ATS scoring
"""
from __future__ import annotations

import io
from typing import Any

from pypdf import PdfReader

from .skills import (
    CERTIFICATION_KEYWORDS,
    EDUCATION_KEYWORDS,
    EXPERIENCE_KEYWORDS,
    PROJECT_KEYWORDS,
    extract_skills,
    keyword_score,
)
from .scoring import score_ats


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_pdf_bytes(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes without writing to disk."""
    reader = PdfReader(io.BytesIO(file_bytes))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def extract_docx_bytes(file_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes without writing to disk."""
    try:
        import docx  # python-docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise RuntimeError(
            "python-docx is not installed. Add 'python-docx' to requirements.txt."
        )


def extract_text(file_bytes: bytes, content_type: str) -> str:
    """Route to the correct extractor based on MIME type."""
    if content_type == "application/pdf":
        return extract_pdf_bytes(file_bytes)
    if content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return extract_docx_bytes(file_bytes)
    raise ValueError(f"Unsupported content type: {content_type}")


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_resume(text: str) -> dict[str, Any]:
    """
    Comprehensive resume analysis:
      - Skills detected
      - ATS score (0-100)
      - Section-level keyword scores
      - Actionable flags and recommendations
    """
    words = text.split()
    skills = extract_skills(text)
    word_count = len(words)

    ats_flags: list[str] = []
    if word_count < 150:
        ats_flags.append(
            f"Resume is very short ({word_count} words). Add project bullets and impact statements."
        )
    if word_count > 1200:
        ats_flags.append(
            "Resume may be too long for ATS. Consider trimming to 1-2 pages."
        )
    if "@" in text:
        ats_flags.append("Email detected. Ensure contact info is in the header, not embedded mid-text.")
    if len(skills) < 5:
        ats_flags.append(
            f"Only {len(skills)} technical skills detected. Add more relevant skills from target roles."
        )
    if not any(kw in text.lower() for kw in PROJECT_KEYWORDS):
        ats_flags.append("No project evidence detected. Add at least 2 project bullets with tech + impact.")

    education_score = keyword_score(text, EDUCATION_KEYWORDS)
    experience_score = keyword_score(text, EXPERIENCE_KEYWORDS)
    certification_score = keyword_score(text, CERTIFICATION_KEYWORDS)
    project_score = keyword_score(text, PROJECT_KEYWORDS)
    ats_score = score_ats(text)

    strengths: list[str] = []
    if len(skills) >= 10:
        strengths.append(f"Strong skill coverage: {len(skills)} skills detected.")
    elif skills:
        strengths.append(f"Detected {len(skills)} technical skills.")
    if experience_score >= 60:
        strengths.append("Good experience signals found in text.")
    if project_score >= 60:
        strengths.append("Project evidence is present.")
    if not strengths:
        strengths.append("Resume text extracted successfully.")

    return {
        "skills": skills,
        "skill_count": len(skills),
        "word_count": word_count,
        "ats_score": ats_score,
        "education_keywords_score": education_score,
        "experience_keywords_score": experience_score,
        "certification_keywords_score": certification_score,
        "project_keywords_score": project_score,
        "strengths": strengths,
        "ats_flags": ats_flags,
        "recommendations": [
            "Add measurable impact (e.g., 'reduced API latency by 40%') to each project bullet.",
            "Tailor skills section keywords to each specific job description before applying.",
            "Use a clean single-column ATS-friendly layout with standard section headings.",
            "Quantify experience: include team size, user count, or performance metrics.",
        ],
    }
