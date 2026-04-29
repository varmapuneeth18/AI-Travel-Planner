from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
LOG_DIR = ROOT_DIR / "logs"
REPORT_DIR = ROOT_DIR / "logs" / "reports"


class Settings(BaseSettings):
    app_name: str = "AI Travel Planner"
    environment: str = "development"
    logs_dir: str = str(LOG_DIR)
    reports_dir: str = str(REPORT_DIR)
    primary_model: str = "gemini-2.5-flash"
    fallback_model: str = "gemini-1.5-flash"
    embeddings_provider: str = "local"
    embeddings_model: str = "text-embedding-3-small"
    vector_store_provider: str = "local"
    vector_store_path: str = str(ROOT_DIR / "logs" / "vector_store.json")
    top_k_retrieval: int = 4
    max_retry_attempts: int = 3
    retry_base_delay_seconds: float = 1.0
    cache_ttl_seconds: int = 1800
    run_token_budget: int = 24000
    enable_rag: bool = True
    enable_caching: bool = True
    enable_evaluation: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)
    return settings
