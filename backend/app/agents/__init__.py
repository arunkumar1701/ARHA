# backend/app/agents/__init__.py
"""ARHA Agent Architecture — 7 independent AI agents."""
from .resume_agent import ResumeAgent
from .company_agent import CompanyIntelAgent
from .job_search_agent import JobSearchAgent
from .matching_agent import JobMatchingAgent
from .notification_agent import NotificationAgent

__all__ = [
    "ResumeAgent",
    "CompanyIntelAgent",
    "JobSearchAgent",
    "JobMatchingAgent",
    "NotificationAgent",
]
