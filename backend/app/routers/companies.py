from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.database import get_db
from app.models import User, CompanyResearch
from app.auth import get_current_user
from app.agents.company_agent import CompanyIntelAgent

router = APIRouter(prefix="/companies", tags=["companies"])

_company_agent = CompanyIntelAgent()


class CompanyResearchRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None


@router.post("/research")
async def research_company(
    payload: CompanyResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run real-time AI research on a company using Tavily + OpenAI."""
    # Check cache — reuse if researched within last 24 hours
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    cached = await db.execute(
        select(CompanyResearch).where(
            CompanyResearch.user_id == current_user.id,
            CompanyResearch.company_name == payload.company_name,
            CompanyResearch.researched_at >= cutoff,
        )
    )
    existing = cached.scalar_one_or_none()
    if existing:
        return {
            "source": "cache",
            "company_name": existing.company_name,
            "trust_score": existing.trust_score,
            "summary": existing.summary,
            "red_flags": existing.red_flags,
            "green_flags": existing.green_flags,
            "news_headlines": existing.news_headlines,
            "glassdoor_rating": existing.glassdoor_rating,
            "researched_at": existing.researched_at.isoformat(),
        }

    # Fresh research via agent
    data = await _company_agent.research(
        company_name=payload.company_name,
        domain=payload.domain,
    )

    import json
    record = CompanyResearch(
        user_id=current_user.id,
        company_name=payload.company_name,
        trust_score=data.get("trust_score"),
        summary=data.get("summary"),
        red_flags=json.dumps(data.get("red_flags", [])),
        green_flags=json.dumps(data.get("green_flags", [])),
        news_headlines=json.dumps(data.get("news_headlines", [])),
        glassdoor_rating=data.get("glassdoor_rating"),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "source": "live",
        "company_name": record.company_name,
        "trust_score": record.trust_score,
        "summary": record.summary,
        "red_flags": json.loads(record.red_flags) if record.red_flags else [],
        "green_flags": json.loads(record.green_flags) if record.green_flags else [],
        "news_headlines": json.loads(record.news_headlines) if record.news_headlines else [],
        "glassdoor_rating": record.glassdoor_rating,
        "researched_at": record.researched_at.isoformat(),
    }


@router.get("/history")
async def company_research_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all companies the user has researched."""
    import json
    result = await db.execute(
        select(CompanyResearch)
        .where(CompanyResearch.user_id == current_user.id)
        .order_by(desc(CompanyResearch.researched_at))
    )
    records = result.scalars().all()
    return {
        "companies": [
            {
                "id": r.id,
                "company_name": r.company_name,
                "trust_score": r.trust_score,
                "glassdoor_rating": r.glassdoor_rating,
                "researched_at": r.researched_at.isoformat(),
            }
            for r in records
        ]
    }


@router.get("/{record_id}")
async def get_company_research(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import json
    result = await db.execute(
        select(CompanyResearch).where(
            CompanyResearch.id == record_id,
            CompanyResearch.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Company research not found")
    return {
        "id": record.id,
        "company_name": record.company_name,
        "trust_score": record.trust_score,
        "summary": record.summary,
        "red_flags": json.loads(record.red_flags) if record.red_flags else [],
        "green_flags": json.loads(record.green_flags) if record.green_flags else [],
        "news_headlines": json.loads(record.news_headlines) if record.news_headlines else [],
        "glassdoor_rating": record.glassdoor_rating,
        "researched_at": record.researched_at.isoformat(),
    }
