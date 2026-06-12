import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


MOCK_JOBS = [
    {
        "id": "job-001",
        "title": "Senior Python Developer",
        "company": "TechCorp",
        "location": "Remote",
        "url": "https://techcorp.com/jobs/001",
        "description": "FastAPI, PostgreSQL, async Python",
        "salary_range": "$120k-$150k",
        "job_type": "full_time",
        "source": "jobicy",
    }
]


@pytest.mark.asyncio
async def test_save_job(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/jobs/save",
        headers=auth_headers,
        json={
            "job_id": "job-001",
            "title": "Senior Python Developer",
            "company": "TechCorp",
            "location": "Remote",
            "url": "https://techcorp.com/jobs/001",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Senior Python Developer"
    assert data["company"] == "TechCorp"


@pytest.mark.asyncio
async def test_save_job_duplicate(client: AsyncClient, auth_headers: dict):
    payload = {
        "job_id": "job-dup",
        "title": "Dup Job",
        "company": "Acme",
        "location": "Remote",
        "url": "https://acme.com/jobs/dup",
    }
    await client.post("/jobs/save", headers=auth_headers, json=payload)
    resp2 = await client.post("/jobs/save", headers=auth_headers, json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_get_saved_jobs(client: AsyncClient, auth_headers: dict):
    response = await client.get("/jobs/saved", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


@pytest.mark.asyncio
async def test_remove_saved_job(client: AsyncClient, auth_headers: dict):
    # First save a job
    save_resp = await client.post(
        "/jobs/save",
        headers=auth_headers,
        json={
            "job_id": "job-to-delete",
            "title": "Delete Me",
            "company": "Corp",
            "location": "Remote",
            "url": "https://corp.com/jobs/del",
        },
    )
    job_id = save_resp.json()["id"]
    del_resp = await client.delete(f"/jobs/saved/{job_id}", headers=auth_headers)
    assert del_resp.status_code == 200


@pytest.mark.asyncio
async def test_search_jobs_requires_auth(client: AsyncClient):
    response = await client.post(
        "/jobs/search", json={"keywords": "python developer"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@patch("app.routers.jobs._search_agent")
async def test_search_jobs_authenticated(mock_agent, client: AsyncClient, auth_headers: dict):
    mock_agent.search = AsyncMock(return_value=MOCK_JOBS)
    response = await client.post(
        "/jobs/search",
        headers=auth_headers,
        json={"keywords": "python developer", "location": "remote"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["jobs"][0]["title"] == "Senior Python Developer"
