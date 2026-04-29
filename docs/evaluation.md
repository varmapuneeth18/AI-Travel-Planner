# Evaluation

The evaluation framework records:

- Latency per agent and per run
- Estimated token usage and cost
- Success/failure rate
- Retry count
- Completeness, faithfulness, relevance, hallucination, and retrieval precision

Artifacts are written to:

- `logs/runs.json`
- `logs/latency.json`
- `logs/costs.json`
- `logs/reports/<run_id>.json`
- `logs/reports/<run_id>.md`
- `logs/reports/<run_id>.csv`

The scoring layer uses lightweight heuristics today so the project can run locally without extra hosted dependencies, while preserving the interfaces needed for stronger evaluator models later.
