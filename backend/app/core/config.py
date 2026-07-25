"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for LottoPilot."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "LottoPilot"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_public_url: str = "http://localhost:8088"
    app_secret_key: str = Field(default="change-me-to-a-long-random-string", min_length=8)
    app_log_level: str = "INFO"
    app_version: str = "0.1.0"
    app_git_commit: str = "dev"
    app_build_time: str = ""

    session_cookie_name: str = "lottopilot_session"
    session_ttl_hours: int = 168
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "lottopilot"
    postgres_user: str = "lottopilot"
    postgres_password: str = "change-me-db-password"
    database_url: str | None = None

    tz: str = "Asia/Shanghai"
    sync_cron_ssq: str = "0 22 * * 2,4,7"
    sync_cron_dlt: str = "5 21 * * 1,3,6"
    sync_enabled: bool = True
    draw_data_source: str = "auto"  # auto|500com|official

    ai_default_timeout_seconds: int = 30
    ai_default_max_tokens: int = 1024
    ai_weight_cap: float = 0.10

    cors_allowed_origins: str = ""
    frontend_dist_dir: str = "frontend_dist"

    @field_validator("ai_weight_cap")
    @classmethod
    def validate_ai_weight_cap(cls, value: float) -> float:
        if value < 0 or value > 0.10:
            raise ValueError("ai_weight_cap must be between 0 and 0.10")
        return value

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def allowed_origins(self) -> list[str]:
        if self.cors_allowed_origins.strip():
            return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]
        return [self.app_public_url.rstrip("/")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
