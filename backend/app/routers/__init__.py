from app.routers.auth import router as auth_router
from app.routers.jobs import router as jobs_router
from app.routers.resume import router as resume_router
from app.routers.companies import router as companies_router

__all__ = ["auth_router", "jobs_router", "resume_router", "companies_router"]
