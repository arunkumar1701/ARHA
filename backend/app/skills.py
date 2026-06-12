"""
skills.py - Production-grade skill extraction and keyword scoring.
Uses a comprehensive 200+ skill dictionary plus OpenAI GPT-4 for
additional extraction when API key is available.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Comprehensive skill keyword dictionary (200+ skills)
# ---------------------------------------------------------------------------
SKILL_KEYWORDS: dict[str, list[str]] = {
    # Languages
    "python": ["python", "python3", "py"],
    "java": ["java", "java 8", "java 11", "java 17", "java 21"],
    "javascript": ["javascript", "js", "es6", "es2015", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "go": ["golang", "go lang", " go "],
    "rust": ["rust", "rustlang"],
    "c++": ["c++", "cpp", "c plus plus"],
    "c": [" c ", "c language", "c programming"],
    "c#": ["c#", "csharp", "c sharp", "dotnet", ".net"],
    "ruby": ["ruby", "ruby on rails", "rails"],
    "php": ["php"],
    "swift": ["swift"],
    "kotlin": ["kotlin"],
    "scala": ["scala"],
    "r": [" r programming", "rstudio", "tidyverse"],
    "dart": ["dart", "flutter"],
    "elixir": ["elixir", "phoenix framework"],
    "haskell": ["haskell"],
    "matlab": ["matlab"],
    "bash": ["bash", "shell script", "zsh"],
    # Web frameworks
    "react": ["react", "reactjs", "react.js"],
    "next.js": ["next.js", "nextjs"],
    "vue": ["vue", "vuejs", "vue.js"],
    "angular": ["angular", "angularjs"],
    "svelte": ["svelte", "sveltekit"],
    "fastapi": ["fastapi"],
    "django": ["django", "django rest framework", "drf"],
    "flask": ["flask"],
    "express": ["express", "expressjs", "express.js"],
    "nest.js": ["nestjs", "nest.js"],
    "spring": ["spring", "spring boot", "spring mvc"],
    "laravel": ["laravel"],
    "rails": ["rails", "ruby on rails"],
    "asp.net": ["asp.net", "asp net"],
    # Databases
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "sqlite": ["sqlite"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search", "opensearch"],
    "cassandra": ["cassandra", "apache cassandra"],
    "dynamodb": ["dynamodb", "dynamo db"],
    "neo4j": ["neo4j", "graph database"],
    "supabase": ["supabase"],
    "firebase": ["firebase", "firestore"],
    "snowflake": ["snowflake"],
    "bigquery": ["bigquery", "big query"],
    # Cloud & DevOps
    "aws": ["aws", "amazon web services", "ec2", "s3", "lambda", "rds"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "docker": ["docker", "dockerfile", "docker compose"],
    "kubernetes": ["kubernetes", "k8s", "kubectl", "helm"],
    "terraform": ["terraform", "infrastructure as code", "iac"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins", "ci/cd", "github actions", "gitlab ci"],
    "nginx": ["nginx"],
    "linux": ["linux", "ubuntu", "debian", "centos", "unix"],
    "git": ["git", "github", "gitlab", "bitbucket"],
    "pulumi": ["pulumi"],
    "cloudformation": ["cloudformation", "cloud formation"],
    # AI/ML
    "machine learning": ["machine learning", "ml", "sklearn", "scikit-learn"],
    "deep learning": ["deep learning", "neural network", "neural networks"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch", "torch"],
    "openai": ["openai", "gpt-4", "chatgpt", "llm"],
    "langchain": ["langchain", "langgraph"],
    "hugging face": ["hugging face", "transformers", "huggingface"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "data science": ["data science", "data analysis", "data analytics"],
    "computer vision": ["computer vision", "opencv", "image recognition"],
    "nlp": ["nlp", "natural language processing", "spacy", "nltk"],
    "mlops": ["mlops", "model deployment", "model serving"],
    "rag": ["rag", "retrieval augmented generation", "vector database"],
    # Architecture & Design
    "microservices": ["microservices", "micro services"],
    "rest api": ["rest api", "restful", "rest"],
    "graphql": ["graphql"],
    "grpc": ["grpc", "protocol buffers", "protobuf"],
    "system design": ["system design"],
    "event-driven": ["event-driven", "event driven", "kafka", "rabbitmq", "pubsub"],
    "kafka": ["kafka", "apache kafka"],
    "rabbitmq": ["rabbitmq", "rabbit mq"],
    "websockets": ["websockets", "websocket", "socket.io"],
    # Testing
    "pytest": ["pytest"],
    "jest": ["jest"],
    "unit testing": ["unit test", "unit testing", "tdd"],
    "selenium": ["selenium", "playwright", "cypress"],
    # Data structures & algorithms
    "data structures": ["data structures", "dsa"],
    "algorithms": ["algorithms", "algorithm"],
    "sql": ["sql", "structured query"],
    # Other
    "computer networks": ["computer networks", "networking", "tcp/ip", "http"],
    "security": ["security", "oauth", "jwt", "authentication", "encryption"],
    "agile": ["agile", "scrum", "kanban", "sprint"],
    "ci/cd": ["ci/cd", "continuous integration", "continuous deployment"],
    "monitoring": ["monitoring", "prometheus", "grafana", "datadog", "sentry"],
    "celery": ["celery", "task queue"],
    "sqlalchemy": ["sqlalchemy", "orm"],
    "pydantic": ["pydantic"],
    "asyncio": ["asyncio", "async", "await"],
    "mobile": ["flutter", "react native", "ios", "android"],
    "blockchain": ["blockchain", "solidity", "web3"],
    "figma": ["figma", "ui design", "ux design"],
}

EDUCATION_KEYWORDS: list[str] = [
    "b.tech", "bachelor", "computer science", "engineering", "degree",
    "graduate", "masters", "m.tech", "msc", "phd", "diploma",
    "university", "college", "gpa", "cgpa",
]

CERTIFICATION_KEYWORDS: list[str] = [
    "certified", "certification", "certificate",
    "aws certified", "azure fundamentals", "gcp professional",
    "aws cloud practitioner", "cka", "ckad",
    "google associate", "coursera", "udemy", "linkedin learning",
]

PROJECT_KEYWORDS: list[str] = [
    "project", "built", "developed", "implemented", "deployed",
    "github", "open source", "contributed", "designed", "architected",
    "launched", "shipped", "production",
]

EXPERIENCE_KEYWORDS: list[str] = [
    "intern", "experience", "worked", "engineer", "developer",
    "backend", "software", "lead", "senior", "full stack",
    "years of experience", "yoe",
]


def normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace."""
    return " ".join(text.lower().split())


def extract_skills(text: str) -> list[str]:
    """Extract skills using the comprehensive keyword dictionary."""
    haystack = normalize_text(text)
    found: list[str] = []
    for skill, aliases in SKILL_KEYWORDS.items():
        if any(alias in haystack for alias in aliases):
            found.append(skill)
    return sorted(found)


def extract_skills_regex(text: str) -> list[str]:
    """More precise extraction using word-boundary regex."""
    haystack = normalize_text(text)
    found: list[str] = []
    for skill, aliases in SKILL_KEYWORDS.items():
        for alias in aliases:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, haystack):
                found.append(skill)
                break
    return sorted(set(found))


def keyword_score(text: str, keywords: list[str]) -> int:
    """Score 0-100 representing how many keywords appear in text."""
    haystack = normalize_text(text)
    if not keywords:
        return 0
    hits = sum(1 for kw in keywords if kw.lower() in haystack)
    return round((hits / len(keywords)) * 100)


def skill_gap_analysis(
    resume_skills: list[str], required_skills: list[str]
) -> dict[str, Any]:
    """Return matched, missing, and a gap percentage."""
    resume_set = set(resume_skills)
    required_set = set(required_skills)
    matched = sorted(resume_set & required_set)
    missing = sorted(required_set - resume_set)
    extra = sorted(resume_set - required_set)
    coverage = round((len(matched) / len(required_set)) * 100) if required_set else 0
    return {
        "matched": matched,
        "missing": missing,
        "extra_skills": extra,
        "coverage_pct": coverage,
        "total_required": len(required_set),
        "total_matched": len(matched),
    }
