from __future__ import annotations

from collections.abc import Iterable
from statistics import mean
from typing import Any

from app.evaluation.metrics import AgentExecutionMetrics, EvaluationSummary, QualityMetrics
from app.schemas.itinerary import TripPlan


class EvaluationService:
    REQUIRED_PLAN_FIELDS = [
        "title",
        "summary",
        "itinerary",
        "hotels_shortlist",
        "budget",
        "packing_list",
    ]

    def evaluate_agent_output(
        self,
        agent_name: str,
        state_before: dict[str, Any],
        result: dict[str, Any],
        retrieved_context: str = "",
    ) -> QualityMetrics:
        completeness = self._completeness_score(result)
        relevance = self._relevance_score(state_before, result)
        faithfulness = self._faithfulness_score(result, retrieved_context)
        hallucination = max(0.0, 1.0 - faithfulness)
        retrieval_precision = self._retrieval_precision(state_before, retrieved_context)
        return QualityMetrics(
            completeness_score=completeness,
            faithfulness_score=faithfulness,
            relevance_score=relevance,
            hallucination_score=hallucination,
            retrieval_precision=retrieval_precision,
        )

    def build_summary(
        self,
        run_id: str,
        agent_metrics: Iterable[AgentExecutionMetrics],
        overall_success: bool,
    ) -> EvaluationSummary:
        metrics = list(agent_metrics)
        aggregate = QualityMetrics(
            completeness_score=self._avg(metric.quality.completeness_score for metric in metrics),
            faithfulness_score=self._avg(metric.quality.faithfulness_score for metric in metrics),
            relevance_score=self._avg(metric.quality.relevance_score for metric in metrics),
            hallucination_score=self._avg(metric.quality.hallucination_score for metric in metrics),
            retrieval_precision=self._avg(metric.quality.retrieval_precision for metric in metrics),
        )
        success_rate = self._avg(1.0 if metric.success else 0.0 for metric in metrics)
        return EvaluationSummary(
            run_id=run_id,
            overall_success=overall_success,
            total_latency_ms=sum(metric.latency_ms for metric in metrics),
            total_retries=sum(metric.retry_count for metric in metrics),
            total_cost_usd=sum(metric.token_usage.estimated_cost_usd for metric in metrics),
            success_rate=success_rate,
            agent_metrics=metrics,
            aggregate_quality=aggregate,
        )

    def _completeness_score(self, result: dict[str, Any]) -> float:
        if "plan" in result:
            plan = result["plan"]
            if isinstance(plan, TripPlan):
                plan_payload = plan.model_dump()
            else:
                plan_payload = plan
            filled = sum(1 for field in self.REQUIRED_PLAN_FIELDS if plan_payload.get(field))
            return round(filled / len(self.REQUIRED_PLAN_FIELDS), 3)

        meaningful_values = [
            value for key, value in result.items() if key not in {"status", "messages"} and value
        ]
        return 1.0 if meaningful_values else 0.0

    def _relevance_score(self, state_before: dict[str, Any], result: dict[str, Any]) -> float:
        spec = state_before.get("spec")
        if not spec:
            return 0.5
        keywords = {
            spec.destination.lower(),
            spec.origin.lower(),
            spec.travel_style.lower(),
            spec.budget_tier.lower(),
            *(interest.lower() for interest in spec.interests),
        }
        haystack = str(result).lower()
        matches = sum(1 for keyword in keywords if keyword and keyword in haystack)
        return round(min(1.0, matches / max(1, len(keywords))), 3)

    def _faithfulness_score(self, result: dict[str, Any], retrieved_context: str) -> float:
        if not retrieved_context:
            return 0.75
        result_text = str(result).lower()
        retrieval_terms = {
            token.strip(".,:;!?()[]{}")
            for token in retrieved_context.lower().split()
            if len(token.strip(".,:;!?()[]{}")) > 4
        }
        if not retrieval_terms:
            return 0.75
        overlap = sum(1 for token in retrieval_terms if token in result_text)
        return round(min(1.0, overlap / min(len(retrieval_terms), 20)), 3)

    def _retrieval_precision(self, state_before: dict[str, Any], retrieved_context: str) -> float:
        if not retrieved_context:
            return 0.0
        spec = state_before.get("spec")
        if not spec:
            return 0.5
        query_terms = {
            spec.destination.lower(),
            spec.travel_style.lower(),
            spec.budget_tier.lower(),
            *(interest.lower() for interest in spec.interests),
        }
        normalized = retrieved_context.lower()
        hits = sum(1 for term in query_terms if term and term in normalized)
        return round(min(1.0, hits / max(1, len(query_terms))), 3)

    def _avg(self, values: Iterable[float]) -> float:
        materialized = list(values)
        if not materialized:
            return 0.0
        return round(mean(materialized), 3)
