from pathlib import Path
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


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def analyze_resume(text: str) -> dict[str, Any]:
    words = text.split()
    skills = extract_skills(text)
    ats_flags = []
    if len(words) < 150:
        ats_flags.append("Resume text is short; add stronger project and impact details.")
    if "@" in text:
        ats_flags.append("Email-like personal data detected; keep private in shared reports.")
    if len(skills) < 5:
        ats_flags.append("Few technical keywords detected; add relevant skills from target roles.")

    education_score = keyword_score(text, EDUCATION_KEYWORDS)
    experience_score = keyword_score(text, EXPERIENCE_KEYWORDS)
    certification_score = keyword_score(text, CERTIFICATION_KEYWORDS)
    project_score = keyword_score(text, PROJECT_KEYWORDS)
    ats_score = round((min(len(skills) * 8, 40) + education_score * 0.2 + experience_score * 0.2 + project_score * 0.2) / 1.0)
    ats_score = max(0, min(100, ats_score))

    return {
        "skills": skills,
        "education_keywords_score": education_score,
        "experience_keywords_score": experience_score,
        "certification_keywords_score": certification_score,
        "project_keywords_score": project_score,
        "ats_score": ats_score,
        "strengths": [
            f"Detected {len(skills)} technical skills." if skills else "Resume text was extracted successfully."
        ],
        "weaknesses": ats_flags,
        "recommendations": [
            "Add measurable impact statements for projects and internships.",
            "Tailor keywords to each verified job before applying.",
            "Keep a clean single-column ATS-friendly layout.",
        ],
    }
