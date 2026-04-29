from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class HealthMonitor:
    max_events: int = 100
    failures: dict[str, deque[str]] = field(default_factory=lambda: defaultdict(deque))

    def record_failure(self, component: str, reason: str) -> None:
        queue = self.failures[component]
        queue.append(reason)
        while len(queue) > self.max_events:
            queue.popleft()

    def status(self) -> dict[str, object]:
        summary = {
            component: {
                "recent_failures": len(reasons),
                "latest_reason": reasons[-1] if reasons else None,
            }
            for component, reasons in self.failures.items()
        }
        return {
            "overall": "degraded" if any(item["recent_failures"] for item in summary.values()) else "ok",
            "components": summary,
        }
