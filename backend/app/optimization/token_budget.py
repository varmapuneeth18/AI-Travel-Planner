from __future__ import annotations

from dataclasses import dataclass


def estimate_token_count(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class TokenBudgetManager:
    max_tokens: int
    consumed_tokens: int = 0

    def can_consume(self, estimated_tokens: int) -> bool:
        return self.consumed_tokens + estimated_tokens <= self.max_tokens

    def consume(self, estimated_tokens: int) -> None:
        if not self.can_consume(estimated_tokens):
            raise ValueError("Token budget exceeded")
        self.consumed_tokens += estimated_tokens

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.consumed_tokens)
