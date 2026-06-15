import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

os.environ["ARHA_DATA_DIR"] = "backend/test-data"
os.environ["ARHA_DB_PATH"] = "backend/test-data/test.sqlite3"

import app.main as main_module  # noqa: E402
from app.config import DB_PATH  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)


async def fake_verify_url(url):
    return {
        "verification_status": "verified",
        "verification_timestamp": "2026-06-11T00:00:00+00:00",
        "http_status": 200,
    }


def make_pdf(path):
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Python FastAPI SQL Docker B.Tech computer science backend project")
    c.save()


def test_resume_upload_encrypts_text():
    init_db()
    pdf = Path("backend/test-data/generated-resume.pdf")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    make_pdf(pdf)

    with pdf.open("rb") as handle:
        response = client.post("/resume/upload", files={"file": ("resume.pdf", handle, "application/pdf")})

    assert response.status_code == 200
    conn = sqlite3.connect(DB_PATH)
    blob = conn.execute("SELECT encrypted_text FROM resumes ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.close()
    assert b"Python FastAPI" not in blob


def test_application_package_requires_approval():
    init_db()
    main_module.verify_url = fake_verify_url
    apply_url = f"https://example.com/{uuid4()}"
    job_response = client.post(
        "/jobs",
        json={
            "title": "Backend Engineer",
            "company": "Example Verified Source",
            "location": "Remote",
            "employment_type": "Full-time",
            "requirements": "Python SQL backend",
            "apply_url": apply_url,
            "source_platform": "Company Career Page",
        },
    )
    assert job_response.status_code == 200
    job_id = job_response.json()["job_id"]

    blocked = client.post(f"/jobs/{job_id}/application-package")
    assert blocked.status_code == 403

    optimization = client.post(f"/jobs/{job_id}/resume-optimization")
    assert optimization.status_code == 200
    optimization_id = optimization.json()["optimization_id"]

    optimization_approval = client.post(
        f"/resume/optimizations/{optimization_id}/decision",
        json={"action": "approve_all", "selected_change_ids": [], "details": {"scope": "test approval"}},
    )
    assert optimization_approval.status_code == 200

    approval = client.post(
        "/approvals",
        json={
            "action_type": "application_package",
            "target_type": "job",
            "target_id": job_id,
            "approved": True,
            "details": {"scope": "prepare local draft only"},
        },
    )
    assert approval.status_code == 200

    package = client.post(f"/jobs/{job_id}/application-package")
    assert package.status_code == 200
    assert package.json()["payload"]["resume_version_id"]
