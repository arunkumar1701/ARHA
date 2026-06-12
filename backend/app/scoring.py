"""
scoring.py - Production-grade ATS and job-match scoring engine.

Weighted scoring model:
  - Skill coverage   45%
  - Experience match 20%
  - Education match  15%
  - Certification    10%
  - Project relevance 10%
"""
from __future__ import annotations

from typing import Any

from .skills import (
    CERTIFICATION_KEYWORDS,
    EDUCATION_KEYWORDS,
    EXPERIENCE_KEYWORDS,
    PROJECT_KEYWORDS,
    extract_skills,
    keyword_score,
    skill_gap_analysis,
)

# Bump this when the formula changes so stored scores can be invalidated
SCORING_FORMULA_VERSION = "2.0.0"


def _category_label(score: int) -> str:
    if score >= 90:
        return "Dream Match"
    if score >= 80:
        return "Excellent Match"
    if score >= 70:
        return "Strong Match"
    if score >= 55:
        return "Moderate Match"
    if score >= 35:
        return "Possible Match"
    return "Low Match"


def score_match(resume_text: str, requirements: str) -> dict[str, Any]:
    """
    Score how well a resume matches a job's requirements.
    Returns a detailed breakdown suitable for display and storage.
    """
    resume_skills = extract_skills(resume_text)
    required_skills = extract_skills(requirements)
    gap = skill_gap_analysis(resume_skills, required_skills)

    skill_match = gap["coverage_pct"]
    education_match = keyword_score(resume_text, EDUCATION_KEYWORDS)
    experience_match = keyword_score(resume_text, EXPERIENCE_KEYWORDS)
    certification_match = keyword_score(resume_text, CERTIFICATION_KEYWORDS)
    project_relevance = keyword_score(resume_text, PROJECT_KEYWORDS)

    overall = round(
        skill_match * 0.45
        + experience_match * 0.20
        + education_match * 0.15
        + certification_match * 0.10
        + project_relevance * 0.10
    )
    overall = max(0, min(100, overall))

    return {
        "overall_score": overall,
        "category": _category_label(overall),
        "skill_match": skill_match,
        "experience_match": experience_match,
        "education_match": education_match,
        "certification_match": certification_match,
        "project_relevance": project_relevance,
        "matched_skills": gap["matched"],
        "missing_skills": gap["missing"],
        "extra_skills": gap["extra_skills"],
        "formula_version": SCORING_FORMULA_VERSION,
    }


def score_ats(resume_text: str) -> int:
    """
    Standalone ATS readability score 0-100.
    Weights: skill density, experience signals, education, project evidence.
    """
    skills = extract_skills(resume_text)
    word_count = len(resume_text.split())

    # Penalise very short resumes
    length_score = min(100, int((word_count / 300) * 100))

    skill_density = min(100, len(skills) * 5)
    education_s = keyword_score(resume_text, EDUCATION_KEYWORDS)
    experience_s = keyword_score(resume_text, EXPERIENCE_KEYWORDS)
    project_s = keyword_score(resume_text, PROJECT_KEYWORDS)
    cert_s = keyword_score(resume_text, CERTIFICATION_KEYWORDS)

    ats = round(
        skill_density * 0.30
        + experience_s * 0.25
        + education_s * 0.20
        + project_s * 0.15
        + cert_s * 0.05
        + length_score * 0.05
    )
    return max(0, min(100, ats))


def build_skill_gap(score: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a prioritised skill-gap roadmap from a score_match result.
    """
    missing = score.get("missing_skills", [])
    roadmap = [
        {
            "skill": skill,
            "priority": "High" if i < 3 else "Medium" if i < 6 else "Low",
            "learning_plan": (
                f"Build a small project or earn a micro-certification demonstrating {skill}."
            ),
        }
        for i, skill in enumerate(missing)
    ]
    return {
        "missing_skills": missing,
        "roadmap": roadmap,
        "resume_improvements": [
            "Add role-specific keywords only when truthful.",
            "Include measurable impact in every project bullet (e.g., reduced latency by 30%).",
            "Ensure resume is in a single-column ATS-friendly format.",
        ],
    }
