from __future__ import annotations

import pandas as pd


def load_metrics_frame(records: list[dict], value_key: str) -> pd.DataFrame:
    rows: list[dict] = []
    for record in records:
        for agent in record.get("agents", []):
            rows.append(
                {
                    "run_id": record.get("run_id"),
                    "status": record.get("status"),
                    "agent_name": agent.get("agent_name"),
                    value_key: agent.get(value_key, 0),
                }
            )
    return pd.DataFrame(rows)
