from __future__ import annotations

import hashlib
from typing import Any


class EmbeddingService:
    def __init__(self, provider: str = "local", model_name: str = "text-embedding-3-small") -> None:
        self.provider = provider
        self.model_name = model_name

    def embed(self, text: str) -> list[float]:
        normalized = text.strip().lower()
        if not normalized:
            return [0.0] * 16
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()
        return [round(byte / 255.0, 6) for byte in digest[:16]]

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        return [self.embed(document) for document in documents]
