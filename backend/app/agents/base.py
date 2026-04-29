from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel


TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class AgentResult(BaseModel):
    content: str
    sources: list[str] = []
    degraded: bool = False


class BaseTravelAgent(Generic[TInput, TOutput]):
    name: str = "base_agent"

    async def run(self, structured_input: TInput) -> TOutput:
        raise NotImplementedError
