# backend/app/models.py
# Full PostgreSQL ORM schema — replaces SQLite tables in db.py
# All sensitive columns stored as encrypted TEXT (Fernet)
from __future__ import annotations

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float,
    ForeignKey, Index, Integer, String, Text, func,
)
from sqlalchemy.orm import relationship

from .database import Base


# ───────────────────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="user")       # user | admin
    is_active = Column(Boolean, default=True)
    telegram_chat_id = Column(String(100))
    notify_email = Column(Boolean, default=True)
    notify_telegram = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(Text, nullable=False)
    file_sha256 = Column(String(64), nullable=False, unique=True)
    encrypted_text = Column(Text, nullable=False)        # Fernet-encrypted resume text
    encrypted_report = Column(Text, nullable=False)      # Fernet-encrypted analysis JSON
    ats_score = Column(Float)
    skills_detected = Column(Text)                       # JSON array string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    optimizations = relationship("ResumeOptimization", back_populates="resume", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_resumes_user_id", "user_id"),)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    resume_id = Column(BigInteger, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(BigInteger, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    version_name = Column(String(255), nullable=False)
    encrypted_text = Column(Text, nullable=False)
    encrypted_change_log = Column(Text)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resume = relationship("Resume", back_populates="versions")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    company = Column(String(500), nullable=False)
    location = Column(String(500))
    employment_type = Column(String(100))
    encrypted_requirements = Column(Text)
    salary = Column(String(200))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    apply_url = Column(Text, nullable=False, unique=True)
    source_platform = Column(String(100))
    posted_date = Column(String(50))
    is_remote = Column(Boolean, default=False)
    experience_level = Column(String(100))
    skills_required = Column(Text)                       # JSON array
    freshness_score = Column(Float, default=1.0)
    discovery_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    verification_status = Column(String(50), default="unverified")
    verification_timestamp = Column(DateTime(timezone=True))
    risk_level = Column(String(100))
    company_assessment = Column(Text)
    company_trust_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    applications = relationship("Application", back_populates="job")
    __table_args__ = (
        Index("ix_jobs_company", "company"),
        Index("ix_jobs_source", "source_platform"),
        Index("ix_jobs_posted_date", "posted_date"),
        Index("ix_jobs_employment_type", "employment_type"),
    )


class Company(Base):
    __tablename__ = "companies"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False, unique=True, index=True)
    website = Column(Text)
    linkedin_url = Column(Text)
    trust_score = Column(Float)                          # 0-100
    trust_category = Column(String(50))                  # Safe | Good | Caution | High Risk
    employee_sentiment = Column(Float)                   # -1.0 to 1.0
    layoff_risk = Column(String(50))                     # Low | Medium | High
    growth_trend = Column(String(50))                    # Growing | Stable | Declining
    funding_status = Column(Text)
    headcount = Column(Integer)
    red_flags = Column(Text)                             # JSON array
    scam_reports = Column(Integer, default=0)
    has_bond_agreement = Column(Boolean, default=False)
    has_fake_recruiters = Column(Boolean, default=False)
    has_unpaid_internships = Column(Boolean, default=False)
    raw_research_json = Column(Text)                     # Full agent output
    last_researched_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ResumeOptimization(Base):
    __tablename__ = "resume_optimizations"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(BigInteger, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    encrypted_report = Column(Text, nullable=False)
    status = Column(String(50), default="pending_approval")
    approved_resume_version_id = Column(BigInteger, ForeignKey("resume_versions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    resume = relationship("Resume", back_populates="optimizations")


class MatchScore(Base):
    __tablename__ = "match_scores"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(BigInteger, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float)
    skill_match = Column(Float)
    experience_match = Column(Float)
    education_match = Column(Float)
    certification_match = Column(Float)
    project_relevance = Column(Float)
    encrypted_details = Column(Text)
    formula_version = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_match_scores_job_resume", "job_id", "resume_id"),)


class Application(Base):
    __tablename__ = "applications"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_version_id = Column(BigInteger, ForeignKey("resume_versions.id"), nullable=True)
    status = Column(String(100), default="pending_approval")
    match_score = Column(Float)
    ats_score_before = Column(Float)
    ats_score_after = Column(Float)
    approval_status = Column(String(50), default="awaiting")  # awaiting | approved | rejected
    approved_at = Column(DateTime(timezone=True))
    applied_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    __table_args__ = (Index("ix_applications_user_job", "user_id", "job_id"),)


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(BigInteger)
    approved = Column(Boolean, nullable=False)
    encrypted_details = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_approvals_user_target", "user_id", "target_type", "target_id"),)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(100), nullable=False)  # new_job | ats_improved | company_risk | interview
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    metadata_json = Column(Text)                          # Extra context JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(200), nullable=False)
    target_type = Column(String(100))
    target_id = Column(BigInteger)
    encrypted_details = Column(Text)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_audit_log_event_type", "event_type"), Index("ix_audit_log_user_id", "user_id"),)
