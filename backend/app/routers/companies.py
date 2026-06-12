"""
routers/companies.py - Company intelligence research endpoints.
Uses CompanyIntelAgent (Tavily + OpenAI). No ORM dependencies.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth import CurrentUser
from app.agents.company_agent import CompanyIntelAgent

router = APIRouter(prefix="/companies", tags=["companies"])
_company_agent = CompanyIntelAgent()


class CompanyResearchRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    include_culture: bool = True
    include_financials: bool = False


@router.post("/research")
async def research_company(
    payload: CompanyResearchRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Research a company using real-time web search via Tavily.
    Returns culture, overview, hiring signals, and key facts.
    """
    result = await _company_agent.research(
        company_name=payload.company_name,
        domain=payload.domain,
        include_culture=payload.include_culture,
        include_financials=payload.include_financials,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not retrieve information for '{payload.company_name}'.",
        )
    return result


@router.get("/search")
async def search_companies(
    q: str,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Quick company name search powered by CompanyIntelAgent."""
    result = await _company_agent.search(query=q)
    return result
