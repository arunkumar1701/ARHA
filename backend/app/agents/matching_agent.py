# backend/app/agents/matching_agent.py
# Agent 5: LLM-powered Job Matching Agent
# Produces explainable match score (0-100) with breakdown
from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from ..config import get_settings

_settings = get_settings()
_client = AsyncOpenAI(api_key=_settings.openai_api_key)


class JobMatchingAgent:
    """Agent 5 — Explainable job matching with breakdown by dimension."""

    async def score(self, resume_text: str, job: dict[str, Any]) -> dict[str, Any]:
        """
        Score how well a resume matches a job.
        Returns overall score + dimension breakdown + explainability report.
        """
        prompt = f"""You are a Technical Recruiter evaluating resume-job fit.

RESUME:
{resume_text[:4000]}

JOB:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Employment Type: {job.get('employment_type', 'N/A')}
Requirements: {job.get('requirements', 'N/A')[:2000]}

Return ONLY valid JSON:
{{
  "overall_score": 0-100,
  "category": "Excellent|Strong|Good|Fair|Poor",
  "skill_match": 0-100,
  "experience_match": 0-100,
  "education_match": 0-100,
  "certification_match": 0-100,
  "project_relevance": 0-100,
  "location_match": 0-100,
  "matching_skills": ["skills found in both"],
  "missing_skills": ["required skills not in resume"],
  "explainability": {{
    "strengths": ["specific reasons this is a good match"],
    "gaps": ["specific gaps found"],
    "recommendation": "Apply|Consider|Skip",
    "reasoning": "2-3 sentence explanation"
  }},
  "formula_version": "llm_v1"
}}"""

        response = await _client.chat.completions.create(
            model=_settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)

    async def build_skill_gap(self, match_result: dict[str, Any]) -> dict[str, Any]:
        """Build learning path from missing skills identified in match result."""
        missing = match_result.get("missing_skills", [])
        if not missing:
            return {"missing_skills": [], "learning_path": [], "gap_percentage": 0}

        prompt = f"""You are a Learning Path Designer.

Missing Skills: {json.dumps(missing)}

Return ONLY valid JSON:
{{
  "missing_skills": {json.dumps(missing)},
  "gap_percentage": 0-100,
  "learning_path": [
    {{
      "skill": "skill name",
      "priority": "High|Medium|Low",
      "estimated_time": "e.g. 2 weeks",
      "courses": [
        {{"title": "course name", "platform": "Coursera|Udemy|YouTube|etc", "url": "URL if known else empty"}}
      ],
      "projects": ["project idea to practice this skill"]
    }}
  ]
}}"""

        response = await _client.chat.completions.create(
            model=_settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
