"""Runtime configuration.

Deliberately unlike OpenTutor's config, which raises unless the database URL is
SQLite. Orrery is multi-tenant from the start, so Postgres is the default and
SQLite is allowed only as a local convenience — the opposite default, and no
hard block in either direction.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Postgres is the target. SQLite is permitted for local runs; unlike the
    # upstream project, neither dialect is rejected at startup.
    database_url: str = "sqlite+aiosqlite:///./orrery.db"

    # Which provider to use: "auto" (Bedrock, then Gemini, then the offline
    # stub — whichever is reachable), or force one of "bedrock" / "gemini" /
    # "stub" explicitly.
    llm_provider: str = "auto"

    # --- AWS Bedrock ---
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-5-20260115-v1:0"
    bedrock_small_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    # When unset, boto3 resolves credentials the usual way (instance role,
    # profile, environment). Only set these for local development.
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # --- Google Gemini (a free-tier alternative to Bedrock) ---
    # Get a key at https://aistudio.google.com/apikey — set as an
    # environment variable, never committed.
    gemini_api_key: str | None = None
    gemini_model_id: str = "gemini-2.5-flash"
    gemini_small_model_id: str = "gemini-2.5-flash-lite"

    # Falls back to a deterministic stub when no provider is reachable, so
    # the app is demoable without any credentials. Set true in production.
    llm_required: bool = False

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
