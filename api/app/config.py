"""Runtime configuration, read from environment variables.

Nothing secret has a default. The app refuses to start in production with
settings that would weaken it (wildcard CORS, plain-http origins).
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"

    # e.g. https://abcdefgh.supabase.co  (no trailing slash needed)
    supabase_url: str

    # Postgres connection string for the API's own low-privilege role.
    database_url: SecretStr

    # Comma-separated list of browser origins allowed to call this API.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    jwt_audience: str = "authenticated"
    db_pool_max_size: int = Field(default=5, ge=1, le=20)

    # LLM providers for STAR feedback (Phase 2)
    groq_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.0-flash"

    # Per-user daily limits
    daily_feedback_limit: int = Field(default=20, ge=1)
    daily_audio_seconds_limit: int = Field(default=600, ge=60)

    @field_validator("supabase_url")
    @classmethod
    def _normalise_supabase_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("https://", "http://")):
            raise ValueError("SUPABASE_URL must start with https://")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _harden_production(self) -> "Settings":
        if self.environment != "production":
            return self
        if not self.supabase_url.startswith("https://"):
            raise ValueError("SUPABASE_URL must be https in production")
        for origin in self.cors_origins:
            if "*" in origin:
                raise ValueError("Wildcard CORS origins are not allowed in production")
            if not origin.startswith("https://"):
                raise ValueError(f"CORS origin must be https in production: {origin}")
        return self

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
