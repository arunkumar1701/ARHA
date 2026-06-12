"""
test_jobs.py - Tests for /jobs endpoints.
JobSearchAgent and db calls are mocked; no real API calls made in CI.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

# Realistic job search response structure (mirrors JobSearchAgent output)
MOCK_SEARCH_RESULT = {
    "jobs": [
        {
            "id": "job-001",
            "title": "Senior Python Developer",
            "company": "TechCorp",
            "location": "Remote",
            "apply_url": "https://techcorp.com/jobs/001",
            "source": "jobicy",
        }
    ],
    "total": 1,
    "page": 1,
}


@pytest.mark.asyncio
async def test_search_jobs_returns_results(client: AsyncClient, auth_headers: dict):
    """GET /jobs/search returns a list of jobs from the search agent."""
    with patch(
        "app.agents.job_search_agent.JobSearchAgent.search",
        new_callable=AsyncMock,
        return_value=MOCK_SEARCH_RESULT,
    ):
        response = await client.get("/jobs/search?q=python+developer")
    assert response.status_code == 200
    body = response.json()
    assert "jobs" in body
    assert body["total"] >= 0


@pytest.mark.asyncio
async def test_search_jobs_requires_query(client: AsyncClient):
    """GET /jobs/search without q param returns 422 unprocessable entity."""
    response = await client.get("/jobs/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_opportunities(client: AsyncClient):
    """GET /jobs/opportunities returns the cached list from PostgreSQL."""
    with patch(
        "app.db.get_opportunities",
        new_callable=AsyncMock,
        return_value=[
            {
                "id": 1,
                "source": "jobicy",
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "apply_url": "https://acme.com/jobs/1",
                "tags": [],
                "verified": True,
                "discovered_at": "2026-06-12T05:00:00",
            }
        ],
    ):
        response = await client.get("/jobs/opportunities")
    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    assert jobs[0]["title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_apply_requires_auth(client: AsyncClient):
    """POST /jobs/apply without auth returns 401."""
    response = await client.post(
        "/jobs/apply",
        json={
            "job_id": "job-001",
            "job_title": "Python Developer",
            "company": "TechCorp",
            "resume_text": "Experienced Python developer with FastAPI skills.",
            "job_description": "Looking for Python developer with FastAPI experience.",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_applications_authenticated(client: AsyncClient, auth_headers: dict):
    """GET /jobs/applications returns the user's application list."""
    with patch(
        "app.db.get_user_applications",
        new_callable=AsyncMock,
        return_value=[
            {
                "id": 1,
                "job_id": "job-001",
                "job_title": "Python Developer",
                "company": "TechCorp",
                "status": "pending",
                "match_score": 0.82,
                "applied_at": "2026-06-12T05:00:00",
            }
        ],
    ):
        response = await client.get("/jobs/applications", headers=auth_headers)
    assert response.status_code == 200
    apps = response.json()
    assert isinstance(apps, list)
