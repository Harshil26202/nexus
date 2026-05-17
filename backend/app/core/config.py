from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://nexus:nexus_secret@localhost:5432/nexus"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 20

    # ─── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET: str = "change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # ─── Azure AI Foundry ─────────────────────────────────────────────────────
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_MINI_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-large"

    # ─── Azure AI Search ──────────────────────────────────────────────────────
    AZURE_AI_SEARCH_ENDPOINT: str = ""
    AZURE_AI_SEARCH_KEY: str = ""
    AZURE_AI_SEARCH_INDEX_CODE: str = "nexus-code-embeddings"
    AZURE_AI_SEARCH_INDEX_INCIDENTS: str = "nexus-incidents"
    AZURE_AI_SEARCH_INDEX_TESTS: str = "nexus-test-history"

    # ─── Azure Service Bus ────────────────────────────────────────────────────
    AZURE_SERVICE_BUS_CONNECTION_STRING: str = ""
    AZURE_SERVICE_BUS_QUEUE_PIPELINE: str = "nexus-pipeline-events"
    AZURE_SERVICE_BUS_QUEUE_INCIDENTS: str = "nexus-incident-events"
    AZURE_SERVICE_BUS_QUEUE_AGENTS: str = "nexus-agent-tasks"

    # ─── Azure Application Insights ───────────────────────────────────────────
    AZURE_APPINSIGHTS_CONNECTION_STRING: str = ""

    # ─── Azure Storage ────────────────────────────────────────────────────────
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_ARTIFACTS: str = "nexus-artifacts"

    # ─── GitHub ───────────────────────────────────────────────────────────────
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_WEBHOOK_SECRET: str = "change_me"

    # ─── Notifications ────────────────────────────────────────────────────────
    SLACK_WEBHOOK_URL: str = ""
    PAGERDUTY_API_KEY: str = ""
    MICROSOFT_TEAMS_WEBHOOK_URL: str = ""

    # ─── Observability ────────────────────────────────────────────────────────
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "nexus-backend"

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
