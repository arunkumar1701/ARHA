from datetime import timezone, datetime
from typing import Any
from urllib.parse import urlparse
import httpx
from .config import INSUFFICIENT_INFO


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


async def verify_url(url: str) -> dict[str, Any]:
    if not valid_url(url):
        return {
            "verification_status": "unverified",
            "verification_timestamp": utc_now(),
            "reason": "Invalid URL.",
        }
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code < 400:
                return {
                    "verification_status": "verified",
                    "verification_timestamp": utc_now(),
                    "http_status": response.status_code,
                }
            return {
                "verification_status": "unverified",
                "verification_timestamp": utc_now(),
                "http_status": response.status_code,
                "reason": INSUFFICIENT_INFO,
            }
    except Exception as exc:
        return {
            "verification_status": "unverified",
            "verification_timestamp": utc_now(),
            "reason": str(exc),
        }


def risk_from_verification(status: str, posted_date: str | None) -> tuple[str, str]:
    if status != "verified":
        return "INSUFFICIENT DATA", INSUFFICIENT_INFO
    if not posted_date:
        return "Yellow Flag", "Source URL is reachable, but posting date was unavailable from the public source."
    return "Green Flag", "Source URL and posting date are available."


async def fetch_jobicy_jobs(tag: str = "software-engineer", count: int = 20) -> list[dict[str, Any]]:
    """Fetch real jobs from Jobicy free API - no API key required."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://jobicy.com/api/v2/remote-jobs",
                params={"tag": tag, "count": count},
            )
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                result = []
                for job in jobs:
                    result.append({
                        "title": job.get("jobTitle", "Software Engineer"),
                        "company": job.get("companyName", "Unknown"),
                        "location": job.get("jobGeo", "Remote"),
                        "employment_type": job.get("jobType", "Full-time"),
                        "requirements": _clean_html(job.get("jobExcerpt", "") or job.get("jobDescription", "")),
                        "salary": job.get("annualSalaryMin") and f"${job['annualSalaryMin']}-${job.get('annualSalaryMax', '?')}",
                        "apply_url": job.get("url", ""),
                        "source_platform": "Jobicy",
                        "posted_date": job.get("pubDate", "")[:10] if job.get("pubDate") else None,
                    })
                return result
    except Exception:
        pass
    return []


async def fetch_arbeitnow_jobs(tag: str = "software-engineer") -> list[dict[str, Any]]:
    """Fetch real jobs from Arbeitnow free API - no API key required."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"page": 1},
            )
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("data", [])
                result = []
                for job in jobs[:20]:
                    title = job.get("title", "")
                    if not any(kw in title.lower() for kw in ["engineer", "developer", "software", "python", "java", "frontend", "backend", "fullstack", "data"]):
                        continue
                    result.append({
                        "title": title,
                        "company": job.get("company_name", "Unknown"),
                        "location": job.get("location", "Remote"),
                        "employment_type": "Full-time" if not job.get("remote") else "Remote / Full-time",
                        "requirements": _clean_html(job.get("description", ""))[:800],
                        "salary": None,
                        "apply_url": job.get("url", ""),
                        "source_platform": "Arbeitnow",
                        "posted_date": job.get("created_at", "")[:10] if job.get("created_at") else None,
                    })
                return result[:10]
    except Exception:
        pass
    return []


async def fetch_remotive_jobs(category: str = "software-dev") -> list[dict[str, Any]]:
    """Fetch real jobs from Remotive free API - no API key required."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://remotive.com/api/remote-jobs",
                params={"category": category, "limit": 20},
            )
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                result = []
                for job in jobs[:15]:
                    result.append({
                        "title": job.get("title", "Software Engineer"),
                        "company": job.get("company_name", "Unknown"),
                        "location": job.get("candidate_required_location", "Remote") or "Remote",
                        "employment_type": job.get("job_type", "full_time").replace("_", " ").title(),
                        "requirements": _clean_html(job.get("description", ""))[:800],
                        "salary": job.get("salary") or None,
                        "apply_url": job.get("url", ""),
                        "source_platform": "Remotive",
                        "posted_date": job.get("publication_date", "")[:10] if job.get("publication_date") else None,
                    })
                return result
    except Exception:
        pass
    return []


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    clean = re.sub(r'<[^>]+>', ' ', text or '')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:1000]


async def fetch_all_live_jobs() -> list[dict[str, Any]]:
    """Fetch live jobs from all free APIs concurrently."""
    import asyncio
    results = await asyncio.gather(
        fetch_jobicy_jobs(tag="software-engineer", count=15),
        fetch_remotive_jobs(category="software-dev"),
        fetch_arbeitnow_jobs(),
        return_exceptions=True,
    )
    all_jobs: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)
    return all_jobs
