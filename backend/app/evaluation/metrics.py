from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class QualityMetrics(BaseModel):
    completeness_score: float = 0.0
    faithfulness_score: float = 0.0
    relevance_score: float = 0.0
    hallucination_score: float = 0.0
    retrieval_precision: float = 0.0


class RetrievalMetrics(BaseModel):
    enabled: bool = False
    query: str | None = None
    top_k: int = 0
    retrieved_ids: list[str] = Field(default_factory=list)
    matched_keywords: int = 0
    precision_at_k: float = 0.0
    injected_context_chars: int = 0


class AgentExecutionMetrics(BaseModel):
    _started_perf: float = PrivateAttr(default=0.0)
    run_id: str
    agent_name: str
    started_at: str = Field(default_factory=utc_now_iso)
    finished_at: str | None = None
    latency_ms: float = 0.0
    success: bool = False
    retry_count: int = 0
    degraded: bool = False
    failure_reason: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    quality: QualityMetrics = Field(default_factory=QualityMetrics)
    retrieval: RetrievalMetrics = Field(default_factory=RetrievalMetrics)
    output_preview: str = ""


class EvaluationSummary(BaseModel):
    run_id: str
    generated_at: str = Field(default_factory=utc_now_iso)
    overall_success: bool = False
    total_latency_ms: float = 0.0
    total_retries: int = 0
    total_cost_usd: float = 0.0
    success_rate: float = 0.0
    agent_metrics: list[AgentExecutionMetrics] = Field(default_factory=list)
    aggregate_quality: QualityMetrics = Field(default_factory=QualityMetrics)


class RunRecord(BaseModel):
    run_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    status: str = "started"
    request_payload: dict[str, Any]
    response_payload: dict[str, Any] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    agent_metrics: list[AgentExecutionMetrics] = Field(default_factory=list)
    evaluation: EvaluationSummary | None = None
