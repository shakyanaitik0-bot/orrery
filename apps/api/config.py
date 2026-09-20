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

    # --- AWS Bedrock ---
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-5-20260115-v1:0"
    bedrock_small_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    # When unset, boto3 resolves credentials the usual way (instance role,
    # profile, environment). Only set these for local development.
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Falls back to a deterministic stub when Bedrock is unreachable, so the
    # app is demoable without AWS credentials. Set true in production.
    llm_required: bool = False

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
