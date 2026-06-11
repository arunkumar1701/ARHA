from typing import Any

from .resume import analyze_resume
from .scoring import score_match
from .skills import extract_skills


STYLE_GUIDANCE = {
    "startup": ["projects", "practical experience", "versatility", "fast learning ability"],
    "product": ["data structures", "algorithms", "system design", "software engineering"],
    "service": ["academic performance", "communication", "teamwork", "general technical skills"],
    "research": ["research work", "publications", "advanced technical knowledge"],
    "internship": ["learning potential", "projects", "academic background", "technical fundamentals"],
}


ROLE_FOCUS = {
    "backend": ["APIs", "Databases", "System Design", "Backend Projects"],
    "cloud": ["AWS", "Azure", "Docker", "Kubernetes"],
    "networking": ["Computer Networks", "Routing", "Protocols", "Network Projects"],
    "ai/ml": ["Machine Learning", "Data Analysis", "Python", "AI Projects"],
}


def infer_role_focus(title: str, requirements: str) -> str:
    text = f"{title} {requirements}".lower()
    if any(word in text for word in ["cloud", "aws", "azure", "docker", "kubernetes"]):
        return "cloud"
    if any(word in text for word in ["network", "routing", "protocol", "tcp"]):
        return "networking"
    if any(word in text for word in ["machine learning", "ml", "ai", "data science"]):
        return "ai/ml"
    return "backend"


def infer_company_style(company: str, title: str, requirements: str, employment_type: str) -> str:
    text = f"{company} {title} {requirements} {employment_type}".lower()
    if "intern" in text:
        return "internship"
    if any(word in text for word in ["research", "lab", "institute"]):
        return "research"
    if any(word in text for word in ["startup", "founding", "equity"]):
        return "startup"
    if any(word in text for word in ["service", "consulting", "client"]):
        return "service"
    return "product"


def _issue(change_id: str, current: str, suggested: str, impact: str, category: str) -> dict[str, str]:
    return {
        "id": change_id,
        "category": category,
        "current_content": current,
        "suggested_content": suggested,
        "estimated_impact": impact,
    }


def generate_resume_optimization(
    resume_text: str,
    job: dict[str, Any],
    alternative_round: int = 0,
) -> dict[str, Any]:
    requirements = job["requirements"]
    before_score = score_match(resume_text, requirements)
    resume_report = analyze_resume(resume_text)
    resume_skills = set(extract_skills(resume_text))
    job_skills = set(extract_skills(requirements))
    missing_skills = sorted(job_skills - resume_skills)

    role_focus = infer_role_focus(job["title"], requirements)
    company_style = infer_company_style(job["company"], job["title"], requirements, job["employment_type"])
    style_keywords = STYLE_GUIDANCE[company_style]
    focus_terms = ROLE_FOCUS[role_focus]

    changes: list[dict[str, str]] = []
    for index, skill in enumerate(missing_skills[:6], start=1):
        changes.append(
            _issue(
                f"keyword-{index}",
                f"No clear evidence of {skill} in the extracted resume text.",
                f"Add a truthful bullet or skills entry demonstrating {skill} with project context.",
                "Improves ATS keyword coverage and recruiter scan alignment.",
                "Missing keyword",
            )
        )

    if resume_report["project_keywords_score"] < 60:
        changes.append(
            _issue(
                "project-impact",
                "Project descriptions appear generic or under-evidenced.",
                "Rewrite one relevant project using action, technology, measurable result, and deployment detail.",
                "Improves project relevance and practical credibility.",
                "Weak project description",
            )
        )

    if resume_report["certification_keywords_score"] < 30:
        changes.append(
            _issue(
                "certification-gap",
                "No strong certification evidence detected.",
                "Add completed relevant certifications, or add a planned certification only outside the resume until earned.",
                "Clarifies verified credentials without fabricating qualifications.",
                "Missing certification",
            )
        )

    changes.append(
        _issue(
            "role-positioning",
            f"Resume is not explicitly positioned for a {role_focus} opportunity.",
            f"Prioritize {', '.join(focus_terms)} in the summary, skills, and strongest project bullets.",
            "Improves company-specific recruiter relevance.",
            "Company-specific positioning",
        )
    )

    changes.append(
        _issue(
            "company-style",
            f"Application materials do not yet reflect {company_style} recruitment style.",
            f"Emphasize {', '.join(style_keywords)} for this company/application type.",
            "Improves adaptive application strategy.",
            "Adaptive application strategy",
        )
    )

    simulated_resume = resume_text + "\n\nTargeted additions to consider:\n" + "\n".join(
        f"- {change['suggested_content']}" for change in changes
    )
    after_score = score_match(simulated_resume, requirements)
    ats_after = analyze_resume(simulated_resume)["ats_score"]

    expected_match_delta = max(0, after_score["overall_score"] - before_score["overall_score"])
    expected_ats_delta = max(0, ats_after - resume_report["ats_score"])

    return {
        "job_id": job["id"],
        "company": job["company"],
        "role": job["title"],
        "role_focus": role_focus,
        "company_style": company_style,
        "current_resume_issues": [change["current_content"] for change in changes],
        "suggested_changes": changes,
        "ats_score_before": resume_report["ats_score"],
        "ats_score_after": ats_after,
        "current_match_score": before_score["overall_score"],
        "potential_match_score": after_score["overall_score"],
        "expected_ats_improvement": expected_ats_delta,
        "expected_match_score_improvement": expected_match_delta,
        "estimated_impact": "High" if expected_match_delta >= 10 or expected_ats_delta >= 10 else "Medium",
        "missing_skills_remaining": missing_skills[6:],
        "suggested_resume_text": simulated_resume,
        "alternative_round": alternative_round,
        "readiness_notes": [
            "Review every suggested claim for truthfulness before approval.",
            "Approved changes create a new encrypted resume version and never overwrite the original.",
        ],
    }
