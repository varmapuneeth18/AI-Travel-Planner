from __future__ import annotations

import csv
import json
from pathlib import Path

from app.evaluation.metrics import EvaluationSummary, RunRecord


class ReportGenerator:
    def __init__(self, reports_dir: str) -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write_run_report(self, run_record: RunRecord) -> dict[str, Path]:
        json_path = self.reports_dir / f"{run_record.run_id}.json"
        markdown_path = self.reports_dir / f"{run_record.run_id}.md"
        csv_path = self.reports_dir / f"{run_record.run_id}.csv"

        json_path.write_text(run_record.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text(self._markdown_summary(run_record), encoding="utf-8")
        self._write_csv(csv_path, run_record)
        return {"json": json_path, "markdown": markdown_path, "csv": csv_path}

    def _markdown_summary(self, run_record: RunRecord) -> str:
        evaluation = run_record.evaluation or EvaluationSummary(
            run_id=run_record.run_id,
            overall_success=run_record.status == "completed",
        )
        lines = [
            f"# Evaluation Summary: {run_record.run_id}",
            "",
            f"- Status: `{run_record.status}`",
            f"- Overall success: `{evaluation.overall_success}`",
            f"- Total latency: `{evaluation.total_latency_ms:.2f} ms`",
            f"- Total retries: `{evaluation.total_retries}`",
            f"- Estimated cost: `${evaluation.total_cost_usd:.4f}`",
            f"- Success rate: `{evaluation.success_rate:.2%}`",
            "",
            "## Aggregate Quality",
            "",
            f"- Completeness: `{evaluation.aggregate_quality.completeness_score:.3f}`",
            f"- Faithfulness: `{evaluation.aggregate_quality.faithfulness_score:.3f}`",
            f"- Relevance: `{evaluation.aggregate_quality.relevance_score:.3f}`",
            f"- Hallucination: `{evaluation.aggregate_quality.hallucination_score:.3f}`",
            f"- Retrieval precision: `{evaluation.aggregate_quality.retrieval_precision:.3f}`",
            "",
            "## Agent Metrics",
            "",
        ]
        for metric in evaluation.agent_metrics:
            lines.extend(
                [
                    f"### {metric.agent_name}",
                    f"- Success: `{metric.success}`",
                    f"- Latency: `{metric.latency_ms:.2f} ms`",
                    f"- Retries: `{metric.retry_count}`",
                    f"- Cost: `${metric.token_usage.estimated_cost_usd:.4f}`",
                    f"- Completeness: `{metric.quality.completeness_score:.3f}`",
                    f"- Faithfulness: `{metric.quality.faithfulness_score:.3f}`",
                    f"- Relevance: `{metric.quality.relevance_score:.3f}`",
                    "",
                ]
            )
        return "\n".join(lines)

    def _write_csv(self, csv_path: Path, run_record: RunRecord) -> None:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "run_id",
                    "agent_name",
                    "success",
                    "latency_ms",
                    "retry_count",
                    "estimated_cost_usd",
                    "completeness_score",
                    "faithfulness_score",
                    "relevance_score",
                    "hallucination_score",
                    "retrieval_precision",
                ],
            )
            writer.writeheader()
            for metric in run_record.agent_metrics:
                writer.writerow(
                    {
                        "run_id": metric.run_id,
                        "agent_name": metric.agent_name,
                        "success": metric.success,
                        "latency_ms": metric.latency_ms,
                        "retry_count": metric.retry_count,
                        "estimated_cost_usd": metric.token_usage.estimated_cost_usd,
                        "completeness_score": metric.quality.completeness_score,
                        "faithfulness_score": metric.quality.faithfulness_score,
                        "relevance_score": metric.quality.relevance_score,
                        "hallucination_score": metric.quality.hallucination_score,
                        "retrieval_precision": metric.quality.retrieval_precision,
                    }
                )
