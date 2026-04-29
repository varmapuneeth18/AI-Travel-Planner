from __future__ import annotations

from typing import Any

from langchain_google_vertexai import ChatVertexAI


class ModelFallbackService:
    def __init__(
        self,
        project: str | None,
        location: str,
        primary_model: str,
        fallback_model: str,
    ) -> None:
        self.project = project
        self.location = location
        self.primary_model = primary_model
        self.fallback_model = fallback_model

    def build_llm(self, model_name: str, temperature: float, max_tokens: int) -> ChatVertexAI:
        return ChatVertexAI(
            model=model_name,
            project=self.project,
            location=self.location,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def invoke_with_fallback(
        self,
        chain_builder: callable,
        payload: dict[str, Any],
        temperature: float = 0.2,
        max_tokens: int = 8000,
    ) -> tuple[Any, bool]:
        primary = self.build_llm(self.primary_model, temperature, max_tokens)
        try:
            response = await chain_builder(primary).ainvoke(payload)
            return response, False
        except Exception:  # noqa: BLE001
            secondary = self.build_llm(self.fallback_model, temperature, max_tokens)
            response = await chain_builder(secondary).ainvoke(payload)
            return response, True
