from __future__ import annotations

from typing import Any

from app.evaluation.metrics import RetrievalMetrics
from app.retriever.embedder import EmbeddingService
from app.retriever.vector_store import LocalVectorStore


class RetrievalService:
    def __init__(self, embedder: EmbeddingService, vector_store: LocalVectorStore, top_k: int = 4) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.top_k = top_k

    def seed_documents(self, documents: list[dict[str, Any]]) -> None:
        prepared = []
        for document in documents:
            content = document["content"]
            prepared.append(
                {
                    **document,
                    "embedding": self.embedder.embed(content),
                }
            )
        self.vector_store.add_documents(prepared)

    def retrieve(self, query: str, expected_terms: list[str] | None = None) -> tuple[str, RetrievalMetrics]:
        query_vector = self.embedder.embed(query)
        hits = self.vector_store.similarity_search(query_vector, self.top_k)
        context = "\n\n".join(hit["content"] for hit in hits)
        expected_terms = expected_terms or []
        matched = sum(1 for term in expected_terms if term.lower() in context.lower())
        precision = matched / max(1, min(self.top_k, len(expected_terms) or 1))
        metrics = RetrievalMetrics(
            enabled=True,
            query=query,
            top_k=self.top_k,
            retrieved_ids=[str(hit.get("id")) for hit in hits],
            matched_keywords=matched,
            precision_at_k=round(min(1.0, precision), 3),
            injected_context_chars=len(context),
        )
        return context, metrics
