from pathlib import Path
from typing import Any
import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import INSUFFICIENT_INFO, UPLOAD_DIR, ensure_data_dirs
from .crypto import crypto_box
from .db import connect, decrypt_json, encrypt_json, init_db, log_event, utc_now
from .jobs import risk_from_verification, verify_url, fetch_all_live_jobs
from .optimizer import generate_resume_optimization
from .resume import analyze_resume, extract_pdf_text
from .scoring import build_skill_gap, score_match

FRONTEND_URL = os.getenv("ARHA_FRONTEND_URL", "http://localhost:5173")
app = FastAPI(title="ARHA V1", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
                allow_origins=["*"],
            allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApprovalIn(BaseModel):
    action_type: str
    target_type: str
    target_id: int
    approved: bool
    details: dict[str, Any] = Field(default_factory=dict)


class JobIn(BaseModel):
    title: str
    company: str
    location: str
    employment_type: str
    requirements: str
    salary: str | None = None
    apply_url: str
    source_platform: str
    posted_date: str | None = None


class OptimizationDecisionIn(BaseModel):
    action: str = Field(pattern="^(approve_all|approve_selected|reject|request_alternative)$")
    selected_change_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported in V1.")

    ensure_data_dirs()
    content = await file.read()
    digest = crypto_box.digest(content)
    stored_path = UPLOAD_DIR / f"{digest}.pdf"
    stored_path.write_bytes(content)
    text = extract_pdf_text(stored_path)
    if not text:
        raise HTTPException(status_code=422, detail="No extractable text found in the PDF.")
    report = analyze_resume(text)

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO resumes(original_filename, stored_path, file_sha256, encrypted_text, encrypted_report, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file.filename,
                str(stored_path),
                digest,
                crypto_box.encrypt(text),
                encrypt_json(report),
                utc_now(),
            ),
        )
        resume_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO resume_versions(resume_id, job_id, version_name, encrypted_text, encrypted_change_log, is_active, created_at)
            VALUES (?, NULL, ?, ?, ?, 1, ?)
            """,
            (
                resume_id,
                "Resume_v1_Original",
                crypto_box.encrypt(text),
                encrypt_json({"changes": ["Original uploaded resume preserved."]}),
                utc_now(),
            ),
        )
    log_event("resume_uploaded", "resume", resume_id, {"filename": file.filename, "sha256": digest})
    return {"resume_id": resume_id, "report": report}


@app.get("/resume/current/report")
def current_resume_report() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM resumes ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
    return {"resume_id": row["id"], "report": decrypt_json(row["encrypted_report"]), "created_at": row["created_at"]}


121

async def search_local() -> dict[str, Any]:
    inserted = []
    with connect() as conn:
        live_jobs = await fetch_all_live_jobs()
        for seed in live_jobs:            verification = await verify_url(seed["apply_url"])
            risk_level, assessment = risk_from_verification(verification["verification_status"], seed["posted_date"])
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO jobs(
                    title, company, location, employment_type, encrypted_requirements, salary, apply_url,
                    source_platform, posted_date, discovery_timestamp, verification_timestamp, verification_status,
                    company_assessment, risk_level, raw_public_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seed["title"],
                    seed["company"],
                    seed["location"],
                    seed["employment_type"],
                    crypto_box.encrypt(seed["requirements"]),
                    seed["salary"],
                    seed["apply_url"],
                    seed["source_platform"],
                    seed["posted_date"],
                    utc_now(),
                    verification["verification_timestamp"],
                    verification["verification_status"],
                    assessment,
                    risk_level,
                    "{}",
                ),
            )
            if cursor.lastrowid:
                inserted.append(int(cursor.lastrowid))
    log_event("public_job_search", "job", None, {"inserted_job_ids": inserted})
124
_job_ids": inserted, "note": "Only public, non-login sources were queried."}


@app.post("/jobs")
async def create_job(job: JobIn) -> dict[str, Any]:
    verification = await verify_url(job.apply_url)
    risk_level, assessment = risk_from_verification(verification["verification_status"], job.posted_date)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO jobs(
                title, company, location, employment_type, encrypted_requirements, salary, apply_url,
                source_platform, posted_date, discovery_timestamp, verification_timestamp, verification_status,
                company_assessment, risk_level, raw_public_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.title,
                job.company,
                job.location,
                job.employment_type,
                crypto_box.encrypt(job.requirements),
                job.salary,
                job.apply_url,
                job.source_platform,
                job.posted_date,
                utc_now(),
                verification["verification_timestamp"],
                verification["verification_status"],
                assessment,
                risk_level,
                "{}",
            ),
        )
        job_id = int(cursor.lastrowid)
    log_event("job_created", "job", job_id, {"source": job.source_platform, "url": job.apply_url})
    return {"job_id": job_id, "verification": verification}


def public_job(row: Any) -> dict[str, Any]:
    requirements = crypto_box.decrypt(row["encrypted_requirements"]) or ""
    recommendation = "Skip" if row["verification_status"] != "verified" or not row["posted_date"] else "Consider"
    return {
        "id": row["id"],
        "company": row["company"],
        "role": row["title"],
        "location": row["location"],
        "employment_type": row["employment_type"],
        "requirements": requirements,
        "salary": row["salary"],
        "apply_url": row["apply_url"],
        "source_platform": row["source_platform"],
        "posted_date": row["posted_date"] or "Unavailable",
        "discovery_timestamp": row["discovery_timestamp"],
        "verification_timestamp": row["verification_timestamp"],
        "verification_status": row["verification_status"],
        "company_assessment": row["company_assessment"],
        "risk_level": row["risk_level"],
        "recommendation": recommendation,
        "approval_required": "YES",
    }


@app.get("/jobs")
def list_jobs() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY discovery_timestamp DESC").fetchall()
    return {"jobs": [public_job(row) for row in rows]}


@app.get("/jobs/{job_id}")
def get_job(job_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
    return public_job(row)


@app.post("/jobs/{job_id}/verify")
async def verify_job(job_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
        verification = await verify_url(row["apply_url"])
        risk_level, assessment = risk_from_verification(verification["verification_status"], row["posted_date"])
        conn.execute(
            "UPDATE jobs SET verification_timestamp = ?, verification_status = ?, risk_level = ?, company_assessment = ? WHERE id = ?",
            (verification["verification_timestamp"], verification["verification_status"], risk_level, assessment, job_id),
        )
    log_event("job_verified", "job", job_id, verification)
    return verification


def latest_resume_row(conn: Any) -> Any:
    row = conn.execute("SELECT * FROM resumes ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Upload a resume before scoring jobs.")
    return row


def get_job_row(conn: Any, job_id: int) -> Any:
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
    return job


def job_context(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"],
        "employment_type": row["employment_type"],
        "requirements": crypto_box.decrypt(row["encrypted_requirements"]) or "",
        "salary": row["salary"],
        "apply_url": row["apply_url"],
        "source_platform": row["source_platform"],
        "posted_date": row["posted_date"],
        "verification_status": row["verification_status"],
        "risk_level": row["risk_level"],
    }


@app.post("/jobs/{job_id}/score")
def score_job(job_id: int) -> dict[str, Any]:
    with connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
        resume = latest_resume_row(conn)
        resume_text = crypto_box.decrypt(resume["encrypted_text"]) or ""
        requirements = crypto_box.decrypt(job["encrypted_requirements"]) or ""
        result = score_match(resume_text, requirements)
        cursor = conn.execute(
            """
            INSERT INTO match_scores(
                job_id, resume_id, overall_score, skill_match, experience_match, education_match,
                certification_match, project_relevance, encrypted_details, formula_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                resume["id"],
                result["overall_score"],
                result["skill_match"],
                result["experience_match"],
                result["education_match"],
                result["certification_match"],
                result["project_relevance"],
                encrypt_json(result),
                result["formula_version"],
                utc_now(),
            ),
        )
        score_id = int(cursor.lastrowid)
    log_event("job_scored", "job", job_id, {"score_id": score_id, "overall_score": result["overall_score"]})
    return {"score_id": score_id, **result}


@app.post("/jobs/{job_id}/skill-gap")
def skill_gap(job_id: int) -> dict[str, Any]:
    score = score_job(job_id)
    gap = build_skill_gap(score)
    log_event("skill_gap_generated", "job", job_id, gap)
    return gap


@app.post("/jobs/{job_id}/resume-optimization")
def resume_optimization(job_id: int) -> dict[str, Any]:
    with connect() as conn:
        job = get_job_row(conn, job_id)
        resume = latest_resume_row(conn)
        resume_text = crypto_box.decrypt(resume["encrypted_text"]) or ""
        report = generate_resume_optimization(resume_text, job_context(job))
        cursor = conn.execute(
            """
            INSERT INTO resume_optimizations(job_id, resume_id, encrypted_report, status, created_at, updated_at)
            VALUES (?, ?, ?, 'pending_approval', ?, ?)
            """,
            (job_id, resume["id"], encrypt_json(report), utc_now(), utc_now()),
        )
        optimization_id = int(cursor.lastrowid)
    log_event("resume_optimization_generated", "job", job_id, {"optimization_id": optimization_id})
    return {"optimization_id": optimization_id, "status": "pending_approval", "report": report}


@app.post("/resume/optimizations/{optimization_id}/decision")
def optimization_decision(optimization_id: int, payload: OptimizationDecisionIn) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM resume_optimizations WHERE id = ?", (optimization_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
        report = decrypt_json(row["encrypted_report"])
        resume = conn.execute("SELECT * FROM resumes WHERE id = ?", (row["resume_id"],)).fetchone()
        if not resume:
            raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
        resume_text = crypto_box.decrypt(resume["encrypted_text"]) or ""

        if payload.action == "reject":
            conn.execute(
                "UPDATE resume_optimizations SET status = 'rejected', updated_at = ? WHERE id = ?",
                (utc_now(), optimization_id),
            )
            status = "rejected"
            version_id = None
        elif payload.action == "request_alternative":
            alt_report = generate_resume_optimization(
                resume_text,
                {
                    "id": report["job_id"],
                    "title": report["role"],
                    "company": report["company"],
                    "employment_type": "Unknown",
                    "requirements": "\n".join(report.get("current_resume_issues", [])),
                },
                alternative_round=int(report.get("alternative_round", 0)) + 1,
            )
            conn.execute(
                "UPDATE resume_optimizations SET encrypted_report = ?, status = 'alternative_suggested', updated_at = ? WHERE id = ?",
                (encrypt_json(alt_report), utc_now(), optimization_id),
            )
            report = alt_report
            status = "alternative_suggested"
            version_id = None
        else:
            selected_ids = set(payload.selected_change_ids)
            changes = report.get("suggested_changes", [])
            approved_changes = changes if payload.action == "approve_all" else [change for change in changes if change["id"] in selected_ids]
            if payload.action == "approve_selected" and not approved_changes:
                raise HTTPException(status_code=400, detail="Select at least one resume change to approve.")
            optimized_text = resume_text + "\n\nApproved ARHA optimization notes:\n" + "\n".join(
                f"- {change['suggested_content']}" for change in approved_changes
            )
            version_name = f"Resume_v{optimization_id}_{report['company'].replace(' ', '_')}_Optimized"
            conn.execute("UPDATE resume_versions SET is_active = 0 WHERE resume_id = ?", (row["resume_id"],))
            cursor = conn.execute(
                """
                INSERT INTO resume_versions(resume_id, job_id, version_name, encrypted_text, encrypted_change_log, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    row["resume_id"],
                    row["job_id"],
                    version_name,
                    crypto_box.encrypt(optimized_text),
                    encrypt_json(
                        {
                            "optimization_id": optimization_id,
                            "action": payload.action,
                            "approved_changes": approved_changes,
                            "expected_ats_improvement": report.get("expected_ats_improvement", 0),
                            "expected_match_score_improvement": report.get("expected_match_score_improvement", 0),
                        }
                    ),
                    utc_now(),
                ),
            )
            version_id = int(cursor.lastrowid)
            conn.execute(
                """
                UPDATE resume_optimizations
                SET status = 'approved', approved_resume_version_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (version_id, utc_now(), optimization_id),
            )
            status = "approved"
    log_event("resume_optimization_decision", "resume_optimization", optimization_id, {"action": payload.action})
    return {"optimization_id": optimization_id, "status": status, "resume_version_id": version_id, "report": report}


@app.get("/resume/versions")
def resume_versions() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM resume_versions ORDER BY created_at DESC").fetchall()
    return {
        "versions": [
            {
                "id": row["id"],
                "resume_id": row["resume_id"],
                "job_id": row["job_id"],
                "version_name": row["version_name"],
                "change_log": decrypt_json(row["encrypted_change_log"]),
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.post("/resume/versions/{version_id}/restore")
def restore_resume_version(version_id: int) -> dict[str, Any]:
    with connect() as conn:
        version = conn.execute("SELECT * FROM resume_versions WHERE id = ?", (version_id,)).fetchone()
        if not version:
            raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
        conn.execute("UPDATE resume_versions SET is_active = 0 WHERE resume_id = ?", (version["resume_id"],))
        conn.execute("UPDATE resume_versions SET is_active = 1 WHERE id = ?", (version_id,))
    log_event("resume_version_restored", "resume_version", version_id, {"resume_id": version["resume_id"]})
    return {"version_id": version_id, "restored": True}


@app.get("/jobs/{job_id}/application-readiness")
def application_readiness(job_id: int) -> dict[str, Any]:
    with connect() as conn:
        job = get_job_row(conn, job_id)
        optimization = conn.execute(
            """
            SELECT * FROM resume_optimizations
            WHERE job_id = ? AND status = 'approved'
            ORDER BY updated_at DESC LIMIT 1
            """,
            (job_id,),
        ).fetchone()
        score = conn.execute(
            "SELECT * FROM match_scores WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    checks = {
        "resume_optimized": bool(optimization),
        "missing_keywords_addressed": bool(optimization),
        "ats_score_acceptable": bool(optimization),
        "skill_gaps_identified": bool(score),
        "company_verified": job["verification_status"] == "verified",
        "job_still_active": job["verification_status"] == "verified",
    }
    ready = all(checks.values())
    return {
        "ready": ready,
        "checks": checks,
        "message": "Application readiness passed." if ready else "Application is not ready. Complete the failed checks before final approval.",
    }


@app.get("/jobs/{job_id}/final-recommendation")
def final_recommendation(job_id: int) -> dict[str, Any]:
    with connect() as conn:
        job = get_job_row(conn, job_id)
        optimization = conn.execute(
            "SELECT * FROM resume_optimizations WHERE job_id = ? ORDER BY updated_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    if not optimization:
        raise HTTPException(status_code=404, detail="Run resume optimization before requesting a final recommendation.")
    report = decrypt_json(optimization["encrypted_report"])
    readiness = application_readiness(job_id)
    return {
        "company": job["company"],
        "role": job["title"],
        "current_match_score": report.get("current_match_score"),
        "potential_match_score_after_resume_changes": report.get("potential_match_score"),
        "ats_score_before": report.get("ats_score_before"),
        "ats_score_after": report.get("ats_score_after"),
        "changes_applied": optimization["status"] == "approved",
        "missing_skills_remaining": report.get("missing_skills_remaining", []),
        "company_suitability": job["risk_level"],
        "recommendation": "Apply" if readiness["ready"] else "Complete readiness checks before applying.",
        "approval_question": "Do you approve the optimized resume and application package for submission?",
        "readiness": readiness,
    }


@app.post("/approvals")
def create_approval(payload: ApprovalIn) -> dict[str, Any]:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO approvals(action_type, target_type, target_id, approved, encrypted_details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.action_type,
                payload.target_type,
                payload.target_id,
                1 if payload.approved else 0,
                encrypt_json(payload.details),
                utc_now(),
            ),
        )
        approval_id = int(cursor.lastrowid)
    log_event("approval_recorded", payload.target_type, payload.target_id, {"approval_id": approval_id, "approved": payload.approved})
    return {"approval_id": approval_id, "approved": payload.approved}


@app.post("/jobs/{job_id}/application-package")
def application_package(job_id: int) -> dict[str, Any]:
    with connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail=INSUFFICIENT_INFO)
        optimization = conn.execute(
            "SELECT * FROM resume_optimizations WHERE job_id = ? AND status = 'approved' ORDER BY updated_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        if not optimization:
            raise HTTPException(status_code=403, detail="Approval of resume optimization is required before preparing an application package.")
        approval = conn.execute(
            """
            SELECT * FROM approvals
            WHERE action_type = 'application_package' AND target_type = 'job' AND target_id = ? AND approved = 1
            ORDER BY id DESC LIMIT 1
            """,
            (job_id,),
        ).fetchone()
        if not approval:
            raise HTTPException(status_code=403, detail="Approval required before preparing an application package.")
        version = conn.execute(
            "SELECT * FROM resume_versions WHERE id = ?",
            (optimization["approved_resume_version_id"],),
        ).fetchone()
        if not version:
            raise HTTPException(status_code=403, detail="Approved optimized resume version is unavailable.")
        payload = {
            "job_id": job_id,
            "resume_id": version["resume_id"],
            "resume_version_id": version["id"],
            "resume_version_name": version["version_name"],
            "cover_letter_draft": "Draft pending AI/local generation. Review and approve before any external sharing.",
            "approval_required_for_submission": True,
        }
        cursor = conn.execute(
            """
            INSERT INTO application_packages(job_id, resume_id, approval_id, encrypted_payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, version["resume_id"], approval["id"], encrypt_json(payload), utc_now()),
        )
        package_id = int(cursor.lastrowid)
    log_event("application_package_prepared", "job", job_id, {"package_id": package_id})
    return {"package_id": package_id, "payload": payload}


@app.get("/audit-log")
def audit_log() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 200").fetchall()
    return {
        "events": [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "target_type": row["target_type"],
                "target_id": row["target_id"],
                "details": decrypt_json(row["encrypted_details"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }
