from datetime import timezone, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import INSUFFICIENT_INFO


PUBLIC_SOURCE_SEEDS = [
    {
        "title": "Software Engineering Roles",
        "company": "Microsoft",
        "location": "India / Remote",
        "employment_type": "Full-time / Internship",
        "requirements": "Public career page index. Open the source URL to review currently available roles.",
        "salary": None,
        "apply_url": "https://jobs.careers.microsoft.com/global/en/search?q=software%20engineer&lc=India",
        "source_platform": "Company Career Page",
        "posted_date": None,
    },
    {
        "title": "Software Engineer Jobs",
        "company": "Google",
        "location": "India",
        "employment_type": "Full-time / Internship",
        "requirements": "Public career page index. Open the source URL to review currently available roles.",
        "salary": None,
        "apply_url": "https://www.google.com/about/careers/applications/jobs/results/?q=Software%20Engineer&location=India",
        "source_platform": "Company Career Page",
        "posted_date": None,
    },
]


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
