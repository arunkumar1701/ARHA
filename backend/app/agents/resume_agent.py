# backend/app/agents/resume_agent.py
# Agent 1: Resume Parser & Analyzer
# Uses OpenAI GPT-4o to extract skills, score ATS, suggest improvements
# No keyword lists — real LLM analysis only
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pypdf import PdfReader

from ..config import get_settings

_settings = get_settings()
_client = AsyncOpenAI(api_key=_settings.openai_api_key)


class ResumeAgent:
    """Agent 1 — Resume Parser, ATS Scorer, and Improvement Suggester."""

    async def extract_text(self, pdf_path: Path) -> str:
        """Extract plain text from a PDF resume."""
        reader = PdfReader(str(pdf_path))
        parts = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(parts).strip()

    async def analyze(self, resume_text: str) -> dict[str, Any]:
        """
        Full LLM-powered resume analysis.
        Returns: skills, education, experience, projects, certifications,
                 ATS score, missing keywords, weaknesses, improvement suggestions.
        """
        prompt = f"""You are a Senior Technical Recruiter and ATS Optimization Expert.

Analyze the following resume and return a detailed JSON report.

RESUME TEXT:
{resume_text[:6000]}

Return ONLY valid JSON with this exact structure:
{{
  "candidate_name": "string or Unknown",
  "skills": ["list of detected technical skills"],
  "education": [{{"degree": "...", "institution": "...", "year": "..."}}],
  "experience": [{{"title": "...", "company": "...", "duration": "...", "summary": "..."}}],
  "projects": [{{"name": "...", "tech_stack": ["..."], "impact": "..."}}],
  "certifications": ["..."],
  "ats_score": 0-100,
  "ats_score_reasoning": "brief explanation",
  "missing_keywords": ["keywords missing for general tech roles"],
  "resume_weaknesses": ["specific weaknesses found"],
  "improvement_suggestions": ["concrete actionable suggestions"],
  "industry_benchmark": "how this resume compares to industry standard",
  "summary": "2 sentence candidate summary"
}}"""

        response = await _client.chat.completions.create(
            model=_settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)

    async def optimize_for_job(
        self,
        resume_text: str,
        job: dict[str, Any],
        alternative_round: int = 0,
    ) -> dict[str, Any]:
        """
        Agent 4 capability: Generate targeted resume optimization suggestions
        for a specific job. Never auto-applies — always requires user approval.
        """
        round_note = (
            f" (Alternative suggestions, round {alternative_round})"
            if alternative_round > 0
            else ""
        )
        prompt = f"""You are a Senior Resume Strategist{round_note}.

Current Resume:
{resume_text[:4000]}

Target Job:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Requirements: {job.get('requirements', 'N/A')[:2000]}
Employment Type: {job.get('employment_type', 'N/A')}

Return ONLY valid JSON:
{{
  "company": "company name",
  "role": "job title",
  "role_focus": "backend|frontend|cloud|ai-ml|networking",
  "company_style": "startup|product|service|research|internship",
  "current_resume_issues": ["list of specific issues vs this JD"],
  "suggested_changes": [
    {{
      "id": "change_1",
      "category": "Skills|Experience|Projects|Summary|Keywords|Certifications",
      "current_content": "exact current text or 'missing'",
      "suggested_content": "exact replacement or addition",
      "estimated_impact": "High|Medium|Low",
      "reason": "why this change helps ATS and recruiter"
    }}
  ],
  "ats_score_before": 0-100,
  "ats_score_after": 0-100,
  "current_match_score": 0-100,
  "potential_match_score": 0-100,
  "expected_ats_improvement": 0-50,
  "expected_match_score_improvement": 0-50,
  "missing_skills_remaining": ["skills still missing after changes"],
  "readiness_notes": ["other things to do before applying"],
  "estimated_impact": "High|Medium|Low",
  "alternative_round": {alternative_round}
}}"""

        response = await _client.chat.completions.create(
            model=_settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.15,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
