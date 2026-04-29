from __future__ import annotations

import json
from math import sqrt
from pathlib import Path
from typing import Any


class LocalVectorStore:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        existing = self._read()
        existing.extend(documents)
        self.storage_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def similarity_search(self, query_vector: list[float], top_k: int = 4) -> list[dict[str, Any]]:
        docs = self._read()
        scored = []
        for doc in docs:
            vector = doc.get("embedding", [])
            score = self._cosine_similarity(query_vector, vector)
            scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def _read(self) -> list[dict[str, Any]]:
        return json.loads(self.storage_path.read_text(encoding="utf-8"))

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = sqrt(sum(a * a for a in left))
        right_norm = sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
