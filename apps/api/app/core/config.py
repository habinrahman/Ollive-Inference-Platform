from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ollive"
    database_ssl: bool = False
    database_ssl_mode: str = "disable"
    database_prepared_statement_cache_size: int = 100
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    ingestion_endpoint: str = "http://localhost:8000/v1/ingest/events"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    allow_mock_provider: bool = Field(default=True)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
