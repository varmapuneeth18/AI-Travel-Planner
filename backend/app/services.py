from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.observability import ObservabilityService
from app.optimization.cache import TTLCache
from app.optimization.token_budget import TokenBudgetManager
from app.resilience.fallback import ModelFallbackService
from app.resilience.health_monitor import HealthMonitor
from app.resilience.retry import RetryConfig
from app.retriever.embedder import EmbeddingService
from app.retriever.retriever import RetrievalService
from app.retriever.vector_store import LocalVectorStore


@dataclass
class AppServices:
    observability: ObservabilityService
    retry_config: RetryConfig
    health_monitor: HealthMonitor
    fallback_models: ModelFallbackService
    cache: TTLCache
    retrieval: RetrievalService
    settings: object


def build_services() -> AppServices:
    settings = get_settings()
    retrieval = RetrievalService(
        embedder=EmbeddingService(
            provider=settings.embeddings_provider,
            model_name=settings.embeddings_model,
        ),
        vector_store=LocalVectorStore(settings.vector_store_path),
        top_k=settings.top_k_retrieval,
    )
    return AppServices(
        observability=ObservabilityService(),
        retry_config=RetryConfig(
            max_attempts=settings.max_retry_attempts,
            base_delay_seconds=settings.retry_base_delay_seconds,
        ),
        health_monitor=HealthMonitor(),
        fallback_models=ModelFallbackService(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            primary_model=settings.primary_model,
            fallback_model=settings.fallback_model,
        ),
        cache=TTLCache(ttl_seconds=settings.cache_ttl_seconds),
        retrieval=retrieval,
        settings=settings,
    )
