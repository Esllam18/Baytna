from __future__ import annotations

import threading
import time
from collections import Counter


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_monotonic = time.monotonic()
        self.requests_total = 0
        self.errors_total = 0
        self.duration_seconds_sum = 0.0
        self.status_counts: Counter[int] = Counter()
        self.method_counts: Counter[str] = Counter()

    def observe(
        self,
        *,
        method: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        with self._lock:
            self.requests_total += 1
            if status_code >= 500:
                self.errors_total += 1
            self.duration_seconds_sum += duration_seconds
            self.status_counts[int(status_code)] += 1
            self.method_counts[method.upper()] += 1

    def snapshot(self) -> dict:
        with self._lock:
            total = self.requests_total
            duration_sum = self.duration_seconds_sum
            return {
                "uptime_seconds": max(0.0, time.monotonic() - self.started_monotonic),
                "requests_total": total,
                "errors_total": self.errors_total,
                "average_duration_ms": (
                    (duration_sum / total) * 1000 if total else 0.0
                ),
                "status_counts": dict(self.status_counts),
                "method_counts": dict(self.method_counts),
            }

    def render_prometheus(self) -> str:
        snapshot = self.snapshot()
        lines = [
            "# HELP baytna_uptime_seconds Process uptime in seconds.",
            "# TYPE baytna_uptime_seconds gauge",
            f"baytna_uptime_seconds {snapshot['uptime_seconds']:.6f}",
            "# HELP baytna_http_requests_total Total HTTP requests observed.",
            "# TYPE baytna_http_requests_total counter",
            f"baytna_http_requests_total {snapshot['requests_total']}",
            "# HELP baytna_http_errors_total Total HTTP 5xx responses observed.",
            "# TYPE baytna_http_errors_total counter",
            f"baytna_http_errors_total {snapshot['errors_total']}",
            "# HELP baytna_http_request_duration_milliseconds_average Average request duration.",
            "# TYPE baytna_http_request_duration_milliseconds_average gauge",
            "baytna_http_request_duration_milliseconds_average "
            f"{snapshot['average_duration_ms']:.6f}",
        ]
        for status, count in sorted(snapshot["status_counts"].items()):
            lines.append(
                f'baytna_http_responses_total{{status="{status}"}} {count}'
            )
        for method, count in sorted(snapshot["method_counts"].items()):
            lines.append(
                f'baytna_http_requests_by_method_total{{method="{method}"}} {count}'
            )
        return "\n".join(lines) + "\n"

    def reset_for_tests(self) -> None:
        with self._lock:
            self.started_monotonic = time.monotonic()
            self.requests_total = 0
            self.errors_total = 0
            self.duration_seconds_sum = 0.0
            self.status_counts.clear()
            self.method_counts.clear()


metrics_registry = MetricsRegistry()
