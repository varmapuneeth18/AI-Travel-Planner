# User Guide

## Planning a Trip

1. Submit a trip request through the frontend wizard or `POST /plan`.
2. The backend orchestrates research, weather, hotel, budget, logistics, activities, and planner stages.
3. The response includes the trip plan plus agent metrics and degraded-mode status.

## Monitoring

Run the dashboard locally:

```bash
streamlit run dashboard/app.py
```

## Experiments

Run the benchmark templates locally:

```bash
python experiments/experiment_runner.py
python experiments/evaluation_pipeline.py
```
