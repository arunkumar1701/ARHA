# backend/app/config.py
# All configuration via environment variables — zero hardcoded secrets
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # ── Core ────────────────────────────────────────────────────────────────
    arha_env: str = "production"

    # ── Security / JWT ───────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_32+_CHARS"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── Encryption (Fernet) ──────────────────────────────────────────────────
    arha_passphrase: str = "CHANGE_ME_IN_PRODUCTION"

    # ── Database (Neon / Supabase PostgreSQL) ────────────────────────────────
    database_url: str = "postgresql+asyncpg://user:pass@localhost/arha"

    # ── Frontend ─────────────────────────────────────────────────────────────
    arha_frontend_url: str = "https://arha-seven.vercel.app"

    # ── OpenAI ───────────────────────────────────────────────────────────────
    openai_api_key: str = ""
        openai_model: str = "gpt-4o"

    # ── Company Intelligence ─────────────────────────────────────────────────
    tavily_api_key: str = ""
    serper_api_key: str = ""

    # ── Caching (Upstash Redis) ──────────────────────────────────────────────
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # ── Notifications ────────────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "noreply@arha.ai"
    telegram_bot_token: str = ""
    admin_email: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 30

    # ── File Storage (ephemeral /tmp on Render) ──────────────────────────────
    upload_dir: Path = Path("/tmp/arha_uploads")

    @field_validator("upload_dir", mode="before")
    @classmethod
    def create_upload_dir(cls, v: str | Path) -> Path:
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        return p

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# ── Shared constants ─────────────────────────────────────────────────────────
INSUFFICIENT_INFO = (
    "I do not currently have sufficient verified information to complete this request."
)


def ensure_data_dirs() -> None:
    get_settings().upload_dir.mkdir(parents=True, exist_ok=True)



# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# Uppercase aliases for compatibility with code using settings.SECRET_KEY etc.
# ---------------------------------------------------------------------------
settings: Settings = get_settings()

# Uppercase shims (read-only property equivalents via module attribute)
# These allow `from .config import settings; settings.SECRET_KEY` to work.
Settings.SECRET_KEY = property(lambda self: self.secret_key)  # type: ignore[attr-defined]
Settings.ALGORITHM = property(lambda self: self.algorithm)  # type: ignore[attr-defined]
Settings.ACCESS_TOKEN_EXPIRE_MINUTES = property(  # type: ignore[attr-defined]
    lambda self: self.access_token_expire_minutes
)
Settings.DATABASE_URL = property(lambda self: self.database_url)  # type: ignore[attr-defined]
Settings.OPENAI_API_KEY = property(lambda self: self.openai_api_key)  # type: ignore[attr-defined]
Settings.TAVILY_API_KEY = property(lambda self: self.tavily_api_key)  # type: ignore[attr-defined]
