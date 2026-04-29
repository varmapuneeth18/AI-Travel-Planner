# Architecture

The production upgrade keeps the existing LangGraph sequence but wraps each node with shared enterprise controls:

- Observability: per-agent metrics, cost estimation, retry counts, and structured logs
- Retrieval: semantic context injection before node execution
- Resilience: retry with exponential backoff and degraded-mode signaling
- Optimization: caching and token budget enforcement
- Reporting: per-run JSON, Markdown, and CSV artifacts

```mermaid
flowchart LR
    API["FastAPI /plan"] --> Graph["LangGraph Workflow"]
    Graph --> R["Research"]
    R --> W["Weather"]
    W --> H["Hotel"]
    H --> B["Budget"]
    B --> L["Logistics"]
    L --> P["Planner"]
    P --> A["Activities"]
    A --> F["Finalize"]
    Graph --> Obs["Observability + Evaluation"]
    Graph --> Rag["Retriever + Vector Store"]
    Graph --> Res["Retry + Fallback + Health"]
    Graph --> Opt["Cache + Token Budget"]
    Obs --> Logs["JSON Logs + Reports"]
```
