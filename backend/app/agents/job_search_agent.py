# backend/app/agents/job_search_agent.py
# Agent 2: Real-time Job Search Agent
# Aggregates from Jobicy, Remotive, Arbeitnow free APIs
# Deduplication, freshness scoring, ranking included
from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import Any

import httpx


class JobSearchAgent:
    """Agent 2 — Multi-source real-time job aggregation with deduplication."""

    # ── Source fetch methods ─────────────────────────────────────────────────────

    async def fetch_jobicy(self, tags: list[str] | None = None, count: int = 20) -> list[dict[str, Any]]:
        """Fetch from Jobicy — no API key required."""
        tag = (tags or ["software-engineer"])[0]
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://jobicy.com/api/v2/remote-jobs",
                    params={"tag": tag, "count": count},
                )
                if resp.status_code == 200:
                    return [
                        self._normalize(job, "Jobicy")
                        for job in resp.json().get("jobs", [])
                    ]
        except Exception:
            pass
        return []

    async def fetch_remotive(self, category: str = "software-dev") -> list[dict[str, Any]]:
        """Fetch from Remotive — no API key required."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://remotive.com/api/remote-jobs",
                    params={"category": category, "limit": 25},
                )
                if resp.status_code == 200:
                    return [
                        self._normalize_remotive(job)
                        for job in resp.json().get("jobs", [])[:20]
                    ]
        except Exception:
            pass
        return []

    async def fetch_arbeitnow(self) -> list[dict[str, Any]]:
        """Fetch from Arbeitnow — no API key required."""
        tech_kw = {"engineer", "developer", "software", "python", "java", "frontend",
                   "backend", "fullstack", "data", "devops", "cloud", "ml", "ai"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://www.arbeitnow.com/api/job-board-api",
                    params={"page": 1},
                )
                if resp.status_code == 200:
                    jobs = resp.json().get("data", [])
                    results = []
                    for job in jobs[:30]:
                        if any(kw in job.get("title", "").lower() for kw in tech_kw):
                            results.append(self._normalize_arbeitnow(job))
                    return results[:15]
        except Exception:
            pass
        return []

    # ── Aggregation pipeline ───────────────────────────────────────────────────

    async def fetch_all(self) -> list[dict[str, Any]]:
        """Fetch from all sources concurrently, deduplicate, rank by freshness."""
        results = await asyncio.gather(
            self.fetch_jobicy(),
            self.fetch_remotive(),
            self.fetch_arbeitnow(),
            return_exceptions=True,
        )

        all_jobs: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                all_jobs.extend(result)

        return self._deduplicate(self._rank(all_jobs))

    def _deduplicate(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate jobs by URL hash and title+company fingerprint."""
        seen_urls: set[str] = set()
        seen_fingerprints: set[str] = set()
        unique: list[dict[str, Any]] = []
        for job in jobs:
            url_key = hashlib.md5(job.get("apply_url", "").encode()).hexdigest()
            fp = hashlib.md5(
                f"{job.get('title', '').lower()}|{job.get('company', '').lower()}".encode()
            ).hexdigest()
            if url_key not in seen_urls and fp not in seen_fingerprints:
                seen_urls.add(url_key)
                seen_fingerprints.add(fp)
                unique.append(job)
        return unique

    def _rank(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank jobs by freshness — newer postings rank higher."""
        now = datetime.now(timezone.utc)

        def freshness(job: dict[str, Any]) -> float:
            posted = job.get("posted_date", "")
            if not posted:
                return 0.3
            try:
                dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_days = (now - dt).days
                return max(0.0, 1.0 - age_days / 60)
            except Exception:
                return 0.3

        return sorted(jobs, key=freshness, reverse=True)

    # ── Normalizers ───────────────────────────────────────────────────────────────

    def _normalize(self, job: dict[str, Any], source: str) -> dict[str, Any]:
        salary_min = job.get("annualSalaryMin")
        salary_max = job.get("annualSalaryMax")
        salary_str = f"${salary_min}-${salary_max}" if salary_min else None
        return {
            "title": job.get("jobTitle", "Software Engineer"),
            "company": job.get("companyName", "Unknown"),
            "location": job.get("jobGeo", "Remote"),
            "employment_type": job.get("jobType", "Full-time"),
            "requirements": self._clean_html(job.get("jobExcerpt", "") or job.get("jobDescription", ""))[:1000],
            "salary": salary_str,
            "salary_min": int(salary_min) if salary_min else None,
            "salary_max": int(salary_max) if salary_max else None,
            "apply_url": job.get("url", ""),
            "source_platform": source,
            "posted_date": (job.get("pubDate", "") or "")[:10] or None,
            "is_remote": True,
            "freshness_score": 1.0,
        }

    def _normalize_remotive(self, job: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": job.get("title", "Software Engineer"),
            "company": job.get("company_name", "Unknown"),
            "location": job.get("candidate_required_location", "Remote") or "Remote",
            "employment_type": job.get("job_type", "full_time").replace("_", " ").title(),
            "requirements": self._clean_html(job.get("description", ""))[:1000],
            "salary": job.get("salary") or None,
            "salary_min": None,
            "salary_max": None,
            "apply_url": job.get("url", ""),
            "source_platform": "Remotive",
            "posted_date": (job.get("publication_date", "") or "")[:10] or None,
            "is_remote": True,
            "freshness_score": 1.0,
        }

    def _normalize_arbeitnow(self, job: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": job.get("title", "Software Engineer"),
            "company": job.get("company_name", "Unknown"),
            "location": job.get("location", "Remote"),
            "employment_type": "Remote / Full-time" if job.get("remote") else "Full-time",
            "requirements": self._clean_html(job.get("description", ""))[:1000],
            "salary": None,
            "salary_min": None,
            "salary_max": None,
            "apply_url": job.get("url", ""),
            "source_platform": "Arbeitnow",
            "posted_date": (job.get("created_at", "") or "")[:10] or None,
            "is_remote": bool(job.get("remote")),
            "freshness_score": 1.0,
        }

    @staticmethod
    def _clean_html(text: str) -> str:
        clean = re.sub(r"<[^>]+>", " ", text or "")
        return re.sub(r"\s+", " ", clean).strip()
