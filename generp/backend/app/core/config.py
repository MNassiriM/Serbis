"""Application configuration via Pydantic BaseSettings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------
    anthropic_api_key: str = Field(..., description="Anthropic API key")

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anon key (public)")
    supabase_service_key: str = Field(..., description="Supabase service role key (secret)")
    database_url: str = Field(
        ..., description="Async PostgreSQL URL (postgresql+asyncpg://...)"
    )
    metadata_database_url: str = Field(
        ..., description="Async PostgreSQL URL for metadata schema"
    )

    # ------------------------------------------------------------------
    # APISIX
    # ------------------------------------------------------------------
    apisix_admin_url: str = Field(
        default="http://apisix:9180", description="APISIX admin API base URL"
    )
    apisix_admin_key: str = Field(
        default="edd1c9f034335f136f87ad84b625c8f1", description="APISIX admin API key"
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    secret_key: str = Field(..., description="Secret key for JWT signing (min 32 chars)")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # ------------------------------------------------------------------
    # LLM model
    # ------------------------------------------------------------------
    llm_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use for agent operations",
    )
    llm_temperature: float = Field(default=0.0)
    llm_max_tokens: int = Field(default=8192)

    @field_validator("secret_key")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            import json

            return json.loads(v)  # type: ignore[no-any-return]
        return v  # type: ignore[return-value]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (singleton)."""
    return Settings()  # type: ignore[call-arg]
