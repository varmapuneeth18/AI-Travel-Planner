from __future__ import annotations

import csv
import json
from pathlib import Path

from experiment_runner import ExperimentRunner, ROOT


def main() -> None:
    runner = ExperimentRunner(ROOT / "experiments" / "dataset.json")
    summary = runner.run()
    output_dir = ROOT / "logs" / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["query", "reliability_score", "cost_efficiency_score", "notes"],
        )
        writer.writeheader()
        for row in summary["results"]:
            writer.writerow(
                {
                    "query": row["query"],
                    "reliability_score": row["reliability_score"],
                    "cost_efficiency_score": row["cost_efficiency_score"],
                    "notes": row["notes"],
                }
            )


if __name__ == "__main__":
    main()
