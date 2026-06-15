"""
cloud_worker.py - Render cron worker for public, non-login job discovery.

Runs on a schedule (e.g., every 6 hours via Render Cron Job).
Fetches live job listings from Jobicy, Remotive, and Arbeitnow APIs,
verifies each apply URL is reachable, and upserts results to PostgreSQL.
No local file storage. No mock data.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

import httpx

from .db import init_db, close_db, upsert_opportunity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source adapters
# ---------------------------------------------------------------------------

async def _fetch_jobicy(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """https://jobicy.com/api/v2/remote-jobs"""
    try:
        r = await client.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 50},
            timeout=15,
        )
        r.raise_for_status()
        jobs = r.json().get("jobs", [])
        results = []
        for j in jobs:
            results.append({
                "source": "jobicy",
                "external_id": str(j.get("id", hashlib.md5(j.get("url", "").encode()).hexdigest())),
                "title": j.get("jobTitle", ""),
                "company": j.get("companyName", ""),
                "location": j.get("jobGeo", "Remote"),
                "apply_url": j.get("url", ""),
                "tags": j.get("jobIndustry", []) + j.get("jobType", []),
                "verified": False,
            })
        return results
    except Exception as exc:
        logger.warning("Jobicy fetch failed: %s", exc)
        return []


async def _fetch_remotive(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """https://remotive.com/api/remote-jobs"""
    try:
        r = await client.get(
            "https://remotive.com/api/remote-jobs",
            params={"limit": 50},
            timeout=15,
        )
        r.raise_for_status()
        jobs = r.json().get("jobs", [])
        results = []
        for j in jobs:
            results.append({
                "source": "remotive",
                "external_id": str(j.get("id", "")),
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "apply_url": j.get("url", ""),
                "tags": j.get("tags", []),
                "verified": False,
            })
        return results
    except Exception as exc:
        logger.warning("Remotive fetch failed: %s", exc)
        return []


async def _fetch_arbeitnow(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """https://www.arbeitnow.com/api/job-board-api"""
    try:
        r = await client.get(
            "https://www.arbeitnow.com/api/job-board-api",
            timeout=15,
        )
        r.raise_for_status()
        jobs = r.json().get("data", [])
        results = []
        for j in jobs:
            results.append({
                "source": "arbeitnow",
                "external_id": j.get("slug", hashlib.md5(j.get("url", "").encode()).hexdigest()),
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", "Remote"),
                "apply_url": j.get("url", ""),
                "tags": j.get("tags", []),
                "verified": False,
            })
        return results
    except Exception as exc:
        logger.warning("Arbeitnow fetch failed: %s", exc)
        return []


async def _verify_url(client: httpx.AsyncClient, url: str) -> bool:
    """HEAD request to confirm the apply URL is still live."""
    if not url:
        return False
    try:
        r = await client.head(url, timeout=8, follow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Cloud worker starting — initialising DB...")

    await init_db()

    async with httpx.AsyncClient(
        headers={"User-Agent": "ARHA-Career-Assistant/2.0 (+https://github.com/arunkumar1701/ARHA)"},
        follow_redirects=True,
    ) as client:
        # Gather listings from all sources concurrently
        jobicy, remotive, arbeitnow = await asyncio.gather(
            _fetch_jobicy(client),
            _fetch_remotive(client),
            _fetch_arbeitnow(client),
        )

        all_jobs = jobicy + remotive + arbeitnow
        logger.info("Fetched %d total listings across all sources.", len(all_jobs))

        # Verify URLs concurrently (batched to avoid hammering servers)
        batch_size = 20
        for i in range(0, len(all_jobs), batch_size):
            batch = all_jobs[i : i + batch_size]
            results = await asyncio.gather(
                *[_verify_url(client, job["apply_url"]) for job in batch]
            )
            for job, ok in zip(batch, results):
                job["verified"] = ok

        verified = sum(1 for j in all_jobs if j["verified"])
        logger.info("%d/%d listings passed URL verification.", verified, len(all_jobs))

        # Upsert all opportunities to PostgreSQL
        upsert_errors = 0
        for job in all_jobs:
            try:
                await upsert_opportunity(job)
            except Exception as exc:
                logger.error("Failed to upsert %s: %s", job.get("external_id"), exc)
                upsert_errors += 1

        logger.info(
            "Cloud worker complete. Upserted %d records, %d errors.",
            len(all_jobs) - upsert_errors,
            upsert_errors,
        )

    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
