"""AI Module configuration.

All settings are loaded from environment variables or a ``.env`` file.
No secret values are hardcoded — defaults are provided only for local
development convenience and must be overridden in any real deployment.

Follows the same pattern as ``backend/app/core/config.py``.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- AI PostgreSQL (async, separate from IAARE backend DB) ---
    AI_DATABASE_URL: str = (
        "postgresql+asyncpg://ai_user:ai_password@localhost:5433/ai_db"
    )

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Qdrant vector store ---
    QDRANT_URL: str = "http://localhost:6333"

    # --- vLLM (OpenAI-compatible inference server) ---
    # Works with self-hosted vLLM OR any hosted OpenAI-compatible endpoint
    # (Together AI, Groq, Fireworks, OpenAI itself, etc.) — just point
    # VLLM_BASE_URL / VLLM_API_KEY / VLLM_MODEL at the hosted provider.
    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    VLLM_API_KEY: str = "EMPTY"
    VLLM_MODEL: str = "Qwen/Qwen3-8B"

    # --- IAARE backend JWT secret (read-only; token validation only) ---
    # No default — must be supplied via environment variable or .env file.
    IAARE_SECRET_KEY: str

    # --- IAARE backend database URL (sync, read-only session) ---
    IAARE_DATABASE_URL: str = "sqlite:///./iaare.db"

    # --- MinIO (object storage for RAG documents) ---
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "rag-documents"

    # --- Celery (RAG ingestion worker) ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"


    @property
    def async_ai_database_url(self) -> str:
        """Normalize AI_DATABASE_URL to the asyncpg driver scheme.

        Render (and most managed Postgres hosts) hand out plain
        `postgresql://` / `postgres://` connection strings, but
        create_async_engine() requires the `postgresql+asyncpg://` scheme.
        """
        url = self.AI_DATABASE_URL
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()


settings = get_ai_settings()
