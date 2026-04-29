from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from charts import load_metrics_frame

ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"


def read_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


st.set_page_config(page_title="Travel Planner Monitoring", layout="wide")
st.title("AI Travel Planner Monitoring Dashboard")

latency_records = read_json(LOGS_DIR / "latency.json")
cost_records = read_json(LOGS_DIR / "costs.json")
run_records = read_json(LOGS_DIR / "runs.json")

latency_df = load_metrics_frame(latency_records, "latency_ms")
cost_df = load_metrics_frame(cost_records, "estimated_cost_usd")

col1, col2, col3 = st.columns(3)
col1.metric("Runs Logged", len(run_records))
col2.metric(
    "Average Agent Latency (ms)",
    round(latency_df["latency_ms"].mean(), 2) if not latency_df.empty else 0,
)
col3.metric(
    "Average Agent Cost (USD)",
    round(cost_df["estimated_cost_usd"].mean(), 4) if not cost_df.empty else 0,
)

st.subheader("Latency Trends")
if not latency_df.empty:
    st.line_chart(latency_df.pivot_table(index="run_id", columns="agent_name", values="latency_ms"))
else:
    st.info("No latency records yet.")

st.subheader("Cost Breakdown")
if not cost_df.empty:
    st.bar_chart(cost_df.pivot_table(index="agent_name", values="estimated_cost_usd", aggfunc="mean"))
else:
    st.info("No cost records yet.")

st.subheader("Failure Rate")
if run_records:
    run_df = pd.DataFrame(run_records)
    if "status" in run_df:
        failure_rate = (run_df["status"] != "completed").mean()
        st.metric("Failure Rate", f"{failure_rate:.2%}")
    st.dataframe(run_df, use_container_width=True)
else:
    st.info("No run records yet.")
