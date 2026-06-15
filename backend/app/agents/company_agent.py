# backend/app/agents/company_agent.py
# Agent 3: Company Intelligence Agent
# Uses Tavily web search + OpenAI to build real Trust Score
# No static data — fully real-time research
from __future__ import annotations

import json
from typing import Any

import httpx
from openai import AsyncOpenAI
from tavily import TavilyClient

from ..config import get_settings

_settings = get_settings()
_openai = AsyncOpenAI(api_key=_settings.openai_api_key)


class CompanyIntelAgent:
    """Agent 3 — Real-time Company Research and Trust Scoring."""

    def __init__(self) -> None:
        self._tavily = TavilyClient(api_key=_settings.tavily_api_key)

    async def research(self, company_name: str, job_title: str = "") -> dict[str, Any]:
        """
        Research a company using Tavily web search + OpenAI analysis.
        Returns trust_score (0-100), category, red flags, sentiment, layoff risk.
        """
        queries = [
            f"{company_name} company reviews employees Glassdoor",
            f"{company_name} scam bond agreement fake recruiter complaints",
            f"{company_name} layoffs funding news 2024 2025",
            f"{company_name} {job_title} salary review interview process",
        ]

        search_results: list[str] = []
        for query in queries:
            try:
                result = self._tavily.search(
                    query=query,
                    search_depth="basic",
                    max_results=3,
                )
                for item in result.get("results", []):
                    content = item.get("content", "")
                    if content:
                        search_results.append(f"SOURCE: {item.get('url', '')}\n{content[:500]}")
            except Exception:
                pass

        research_text = "\n\n".join(search_results[:12]) if search_results else "No search results found."

        prompt = f"""You are a Company Intelligence Analyst. Analyze this company based on real search results.

Company: {company_name}
Job: {job_title}

Search Results:
{research_text[:5000]}

Return ONLY valid JSON:
{{
  "company_name": "{company_name}",
  "trust_score": 0-100,
  "trust_category": "Safe|Good|Caution|High Risk",
  "employee_sentiment": -1.0 to 1.0,
  "layoff_risk": "Low|Medium|High|Unknown",
  "growth_trend": "Growing|Stable|Declining|Unknown",
  "funding_status": "string describing funding stage or 'Unknown'",
  "red_flags": ["list of specific red flags found, empty if none"],
  "scam_reports": 0,
  "has_bond_agreement": true/false,
  "has_fake_recruiters": true/false,
  "has_unpaid_internships": true/false,
  "headcount": estimated number or null,
  "summary": "2-3 sentence company assessment",
  "data_sources": ["list of sources used"]
}}

Trust Score Guide: 80-100=Safe, 60-79=Good, 40-59=Caution, 0-39=High Risk.
Reduce score for: scam reports, bond requirements, fake recruiters, unpaid internships, layoffs, poor reviews."""

        response = await _openai.chat.completions.create(
            model=_settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw)
        result["raw_research_json"] = json.dumps({"queries": queries, "results_count": len(search_results)})
        return result

    def get_risk_level(self, trust_score: float) -> str:
        """Convert trust score to display risk level."""
        if trust_score >= 80:
            return "Green Flag"
        if trust_score >= 60:
            return "Yellow Flag"
        if trust_score >= 40:
            return "Orange Flag"
        return "Red Flag"
