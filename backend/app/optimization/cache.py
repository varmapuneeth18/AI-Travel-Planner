from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TTLCache:
    ttl_seconds: int
    store: dict[str, tuple[float, Any]] = field(default_factory=dict)

    def get(self, key: str) -> Any | None:
        entry = self.store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            self.store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self.store[key] = (time.time() + self.ttl_seconds, value)
