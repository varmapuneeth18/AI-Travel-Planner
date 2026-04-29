from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    multiplier: float = 2.0


async def retry_async(
    func: Callable[[], Awaitable[T]],
    config: RetryConfig,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= config.max_attempts:
                break
            if on_retry:
                on_retry(attempt, exc)
            await asyncio.sleep(config.base_delay_seconds * (config.multiplier ** (attempt - 1)))
    assert last_error is not None
    raise last_error
