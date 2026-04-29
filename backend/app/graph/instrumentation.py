from __future__ import annotations

from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Any

from app.evaluation.metrics import RetrievalMetrics
from app.resilience.retry import retry_async
from app.services import AppServices


NodeHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def instrument_node(agent_name: str, handler: NodeHandler, services: AppServices) -> NodeHandler:
    async def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        run_id = state.get("run_id", "unknown")
        metric = services.observability.start_agent_metric(run_id=run_id, agent_name=agent_name)
        state_before = deepcopy(state)
        retry_count = 0
        degraded = False
        failure_reason = None
        retrieval_context = ""
        retrieval_metrics = RetrievalMetrics(enabled=False)

        cache_key = f"{agent_name}:{hash(str(state_before.get('spec')))}:{state_before.get('revision_count', 0)}"
        if services.settings.enable_caching:
            cached = services.cache.get(cache_key)
            if cached is not None:
                cached["_cached"] = True
                return cached

        if services.settings.enable_rag and state_before.get("spec"):
            spec = state_before["spec"]
            query = " ".join(
                [
                    spec.destination,
                    spec.travel_style,
                    spec.budget_tier,
                    *spec.interests,
                ]
            )
            retrieval_context, retrieval_metrics = services.retrieval.retrieve(
                query=query,
                expected_terms=[spec.destination, spec.travel_style, spec.budget_tier, *spec.interests],
            )
            state["retrieval_context"] = retrieval_context
            state["retrieval_metrics"] = retrieval_metrics.model_dump()

        async def attempt() -> dict[str, Any]:
            return await handler(state)

        def on_retry(attempt_number: int, exc: Exception) -> None:
            nonlocal retry_count
            retry_count = attempt_number
            services.health_monitor.record_failure(agent_name, str(exc))

        try:
            result = await retry_async(attempt, services.retry_config, on_retry=on_retry)
        except Exception as exc:  # noqa: BLE001
            failure_reason = str(exc)
            degraded = True
            result = {"status": "failed", "messages": [failure_reason], "degraded": True}

        result_text = str(result)
        prompt_text = f"{state_before}\n\n{retrieval_context}"
        token_usage = services.observability.estimate_token_usage(prompt_text, result_text)
        metric = services.observability.complete_agent_metric(
            metric=metric,
            state_before=state_before,
            result=result,
            retry_count=retry_count,
            degraded=degraded,
            failure_reason=failure_reason,
            retrieval_context=retrieval_context,
            token_usage=token_usage,
        )
        metric.retrieval = retrieval_metrics
        state_metrics = list(state.get("agent_metrics", []))
        state_metrics.append(metric.model_dump())
        result["agent_metrics"] = state_metrics
        result["degraded"] = degraded or result.get("degraded", False)
        if services.settings.enable_caching and failure_reason is None:
            services.cache.set(cache_key, result)
        return result

    return wrapped
