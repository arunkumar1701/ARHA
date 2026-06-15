from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    return [item.strip() for item in value.split(",") if item.strip()]


CsvList = Annotated[list[str], BeforeValidator(_split_csv)]

INSUFFICIENT_INFO = (
    "I do not currently have sufficient verified information to complete this request."
)


class Settings(BaseSettings):
    arha_env: str = "production"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    arha_passphrase: str = ""

    database_url: str = ""
    arha_frontend_url: str = "http://localhost:5173"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    tavily_api_key: str = ""
    serper_api_key: str = ""
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = ""
    telegram_bot_token: str = ""
    admin_email: str = ""

    cors_origins: CsvList = Field(default_factory=lambda: ["http://localhost:5173"])
    allowed_hosts: CsvList = Field(default_factory=lambda: ["localhost", "127.0.0.1", "testserver"])
    rate_limit_per_minute: int = Field(default=30, ge=1, le=1000)
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def environment(self) -> str:
        return self.arha_env.lower()

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        if self.is_testing:
            return self

        required = {
            "DATABASE_URL": self.database_url,
            "SECRET_KEY": self.secret_key,
            "ARHA_PASSPHRASE": self.arha_passphrase,
            "OPENAI_API_KEY": self.openai_api_key,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(sorted(missing))
            )
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters.")
        if len(self.arha_passphrase) < 16:
            raise ValueError("ARHA_PASSPHRASE must be at least 16 characters.")
        if not self.database_url.startswith(
            ("postgresql+asyncpg://", "postgresql://", "postgres://")
        ):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
