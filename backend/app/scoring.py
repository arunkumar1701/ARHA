from typing import Any

from .config import SCORING_FORMULA_VERSION
from .skills import (
    CERTIFICATION_KEYWORDS,
    EDUCATION_KEYWORDS,
    EXPERIENCE_KEYWORDS,
    PROJECT_KEYWORDS,
    extract_skills,
    keyword_score,
)


def score_match(resume_text: str, requirements: str) -> dict[str, Any]:
    resume_skills = set(extract_skills(resume_text))
    required_skills = set(extract_skills(requirements))
    matched_skills = sorted(resume_skills & required_skills)
    missing_skills = sorted(required_skills - resume_skills)

    if required_skills:
        skill_match = round((len(matched_skills) / len(required_skills)) * 100)
    else:
        skill_match = 0

    education_match = keyword_score(resume_text + " " + requirements, EDUCATION_KEYWORDS)
    experience_match = keyword_score(resume_text + " " + requirements, EXPERIENCE_KEYWORDS)
    certification_match = keyword_score(resume_text + " " + requirements, CERTIFICATION_KEYWORDS)
    project_relevance = keyword_score(resume_text + " " + requirements, PROJECT_KEYWORDS)

    overall = round(
        skill_match * 0.45
        + education_match * 0.15
        + experience_match * 0.2
        + certification_match * 0.1
        + project_relevance * 0.1
    )

    category = (
        "Dream Match"
        if overall >= 90
        else "Excellent Match"
        if overall >= 80
        else "Strong Match"
        if overall >= 70
        else "Moderate Match"
        if overall >= 50
        else "Low Match"
    )

    return {
        "overall_score": overall,
        "category": category,
        "skill_match": skill_match,
        "experience_match": experience_match,
        "education_match": education_match,
        "certification_match": certification_match,
        "project_relevance": project_relevance,
        "matched_evidence": {"skills": matched_skills},
        "missing_evidence": {"skills": missing_skills},
        "formula_version": SCORING_FORMULA_VERSION,
    }


def build_skill_gap(score: dict[str, Any]) -> dict[str, Any]:
    missing = score.get("missing_evidence", {}).get("skills", [])
    roadmap = []
    for index, skill in enumerate(missing, start=1):
        priority = "High" if index <= 3 else "Medium"
        roadmap.append(
            {
                "skill": skill,
                "priority": priority,
                "learning_plan": f"Build one small project or certification artifact demonstrating {skill}.",
            }
        )
    return {
        "missing_skills": missing,
        "roadmap": roadmap,
        "resume_improvements_needed": [
            "Add role-specific keywords only when they are truthful.",
            "Add project bullets that prove the required backend/cloud/DSA skills.",
        ],
    }
