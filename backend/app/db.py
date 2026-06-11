import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import DB_PATH, ensure_data_dirs
from .crypto import crypto_box


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_data_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                encrypted_text BLOB NOT NULL,
                encrypted_report BLOB NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                employment_type TEXT NOT NULL,
                encrypted_requirements BLOB NOT NULL,
                salary TEXT,
                apply_url TEXT NOT NULL UNIQUE,
                source_platform TEXT NOT NULL,
                posted_date TEXT,
                discovery_timestamp TEXT NOT NULL,
                verification_timestamp TEXT,
                verification_status TEXT NOT NULL,
                company_assessment TEXT NOT NULL DEFAULT 'INSUFFICIENT DATA',
                risk_level TEXT NOT NULL DEFAULT 'INSUFFICIENT DATA',
                raw_public_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS match_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                overall_score INTEGER NOT NULL,
                skill_match INTEGER NOT NULL,
                experience_match INTEGER NOT NULL,
                education_match INTEGER NOT NULL,
                certification_match INTEGER NOT NULL,
                project_relevance INTEGER NOT NULL,
                encrypted_details BLOB NOT NULL,
                formula_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id),
                FOREIGN KEY(resume_id) REFERENCES resumes(id)
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                approved INTEGER NOT NULL,
                encrypted_details BLOB NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS application_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                approval_id INTEGER NOT NULL,
                encrypted_payload BLOB NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id),
                FOREIGN KEY(resume_id) REFERENCES resumes(id),
                FOREIGN KEY(approval_id) REFERENCES approvals(id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                target_type TEXT,
                target_id INTEGER,
                encrypted_details BLOB NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resume_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                job_id INTEGER,
                version_name TEXT NOT NULL,
                encrypted_text BLOB NOT NULL,
                encrypted_change_log BLOB NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(resume_id) REFERENCES resumes(id),
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS resume_optimizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                encrypted_report BLOB NOT NULL,
                status TEXT NOT NULL,
                approved_resume_version_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id),
                FOREIGN KEY(resume_id) REFERENCES resumes(id),
                FOREIGN KEY(approved_resume_version_id) REFERENCES resume_versions(id)
            );
            """
        )


def encrypt_json(data: dict[str, Any]) -> bytes:
    return crypto_box.encrypt(json.dumps(data, sort_keys=True)) or b""


def decrypt_json(blob: bytes | None) -> dict[str, Any]:
    if not blob:
        return {}
    text = crypto_box.decrypt(blob)
    return json.loads(text or "{}")


def log_event(event_type: str, target_type: str | None, target_id: int | None, details: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO audit_log(event_type, target_type, target_id, encrypted_details, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_type, target_type, target_id, encrypt_json(details), utc_now()),
        )
