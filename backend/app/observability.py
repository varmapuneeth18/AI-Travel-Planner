from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.evaluation.evaluator import EvaluationService
from app.evaluation.metrics import AgentExecutionMetrics, RunRecord, TokenUsage, utc_now_iso
from app.evaluation.report_generator import ReportGenerator


class ObservabilityService:
    def __init__(self) -> None:
        settings = get_settings()
        self.logs_dir = Path(settings.logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.runs_path = self.logs_dir / "runs.json"
        self.latency_path = self.logs_dir / "latency.json"
        self.costs_path = self.logs_dir / "costs.json"
        self.evaluator = EvaluationService()
        self.report_generator = ReportGenerator(settings.reports_dir)
        for path in [self.runs_path, self.latency_path, self.costs_path]:
            if not path.exists():
                path.write_text("[]", encoding="utf-8")

    def create_run_record(self, run_id: str, request_payload: dict[str, Any]) -> RunRecord:
        return RunRecord(run_id=run_id, request_payload=request_payload)

    def finalize_run_record(self, run_record: RunRecord) -> None:
        run_record.agent_metrics = [self._coerce_metric(metric) for metric in run_record.agent_metrics]
        run_record.evaluation = self.evaluator.build_summary(
            run_id=run_record.run_id,
            agent_metrics=run_record.agent_metrics,
            overall_success=run_record.status == "completed",
        )
        run_record.total_latency_ms = run_record.evaluation.total_latency_ms
        run_record.total_cost_usd = run_record.evaluation.total_cost_usd
        self._append_json(self.runs_path, run_record.model_dump(mode="json"))
        self._append_json(self.latency_path, self._latency_snapshot(run_record))
        self._append_json(self.costs_path, self._cost_snapshot(run_record))
        self.report_generator.write_run_report(run_record)

    def start_agent_metric(self, run_id: str, agent_name: str) -> AgentExecutionMetrics:
        metric = AgentExecutionMetrics(run_id=run_id, agent_name=agent_name)
        metric._started_perf = time.perf_counter()
        return metric

    def complete_agent_metric(
        self,
        metric: AgentExecutionMetrics,
        state_before: dict[str, Any],
        result: dict[str, Any],
        retry_count: int,
        degraded: bool,
        failure_reason: str | None,
        retrieval_context: str = "",
        token_usage: TokenUsage | None = None,
    ) -> AgentExecutionMetrics:
        started = metric._started_perf or time.perf_counter()
        metric.finished_at = utc_now_iso()
        metric.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        metric.success = failure_reason is None
        metric.retry_count = retry_count
        metric.degraded = degraded
        metric.failure_reason = failure_reason
        metric.output_preview = str(result)[:500]
        if token_usage:
            metric.token_usage = token_usage
        metric.quality = self.evaluator.evaluate_agent_output(
            agent_name=metric.agent_name,
            state_before=state_before,
            result=result,
            retrieved_context=retrieval_context,
        )
        return metric

    def estimate_token_usage(self, prompt_text: str, response_text: str) -> TokenUsage:
        prompt_tokens = max(1, len(prompt_text) // 4)
        completion_tokens = max(1, len(response_text) // 4)
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = round((total_tokens / 1000) * 0.00035, 6)
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
        )

    def _append_json(self, path: Path, payload: dict[str, Any]) -> None:
        content = json.loads(path.read_text(encoding="utf-8"))
        content.append(payload)
        path.write_text(json.dumps(content, indent=2), encoding="utf-8")

    def _latency_snapshot(self, run_record: RunRecord) -> dict[str, Any]:
        metrics = [self._coerce_metric(metric) for metric in run_record.agent_metrics]
        return {
            "run_id": run_record.run_id,
            "status": run_record.status,
            "total_latency_ms": run_record.total_latency_ms,
            "agents": [
                {
                    "agent_name": metric.agent_name,
                    "latency_ms": metric.latency_ms,
                    "success": metric.success,
                }
                for metric in metrics
            ],
        }

    def _cost_snapshot(self, run_record: RunRecord) -> dict[str, Any]:
        metrics = [self._coerce_metric(metric) for metric in run_record.agent_metrics]
        return {
            "run_id": run_record.run_id,
            "status": run_record.status,
            "total_cost_usd": run_record.total_cost_usd,
            "agents": [
                {
                    "agent_name": metric.agent_name,
                    "estimated_cost_usd": metric.token_usage.estimated_cost_usd,
                    "total_tokens": metric.token_usage.total_tokens,
                }
                for metric in metrics
            ],
        }

    def _coerce_metric(self, metric: AgentExecutionMetrics | dict[str, Any]) -> AgentExecutionMetrics:
        if isinstance(metric, AgentExecutionMetrics):
            return metric
        return AgentExecutionMetrics.model_validate(metric)
