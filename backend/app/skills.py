SKILL_KEYWORDS = {
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "react": ["react"],
    "node.js": ["node.js", "nodejs", "node"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "sql": ["sql", "postgres", "mysql", "sqlite"],
    "mongodb": ["mongodb", "mongo"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "azure": ["azure"],
    "aws": ["aws", "amazon web services"],
    "git": ["git", "github"],
    "linux": ["linux"],
    "rest api": ["rest api", "restful", "api"],
    "data structures": ["data structures", "dsa"],
    "algorithms": ["algorithms"],
    "computer networks": ["computer networks", "networking", "tcp/ip"],
    "machine learning": ["machine learning", "ml"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
}

EDUCATION_KEYWORDS = ["b.tech", "bachelor", "computer science", "engineering", "degree", "graduate"]
CERTIFICATION_KEYWORDS = ["certified", "certification", "certificate", "azure fundamentals", "aws cloud practitioner"]
PROJECT_KEYWORDS = ["project", "built", "developed", "implemented", "deployed", "github"]
EXPERIENCE_KEYWORDS = ["intern", "experience", "worked", "engineer", "developer", "backend", "software"]


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def extract_skills(text: str) -> list[str]:
    haystack = normalize_text(text)
    found = []
    for skill, aliases in SKILL_KEYWORDS.items():
        if any(alias in haystack for alias in aliases):
            found.append(skill)
    return sorted(found)


def keyword_score(text: str, keywords: list[str]) -> int:
    haystack = normalize_text(text)
    hits = sum(1 for keyword in keywords if keyword in haystack)
    if not keywords:
        return 0
    return round((hits / len(keywords)) * 100)
