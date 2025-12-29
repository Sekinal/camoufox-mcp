"""
Metrics collection for Camoufox MCP Server.

Provides in-memory metrics tracking for tool calls, performance, and errors.
Suitable for single-session Docker deployments.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass
class ToolMetrics:
    """Metrics for a single tool."""

    call_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    durations: list[float] = field(default_factory=list)
    last_error: str | None = None
    last_error_time: datetime | None = None
    last_call_time: datetime | None = None

    @property
    def avg_duration_ms(self) -> float:
        """Average duration in milliseconds."""
        return self.total_duration_ms / self.call_count if self.call_count > 0 else 0.0

    @property
    def error_rate(self) -> float:
        """Error rate as a percentage."""
        return (self.error_count / self.call_count * 100) if self.call_count > 0 else 0.0

    @property
    def p50_duration_ms(self) -> float:
        """50th percentile (median) duration."""
        return statistics.median(self.durations) if self.durations else 0.0

    @property
    def p95_duration_ms(self) -> float:
        """95th percentile duration."""
        if len(self.durations) < 2:
            return self.durations[0] if self.durations else 0.0
        return statistics.quantiles(self.durations, n=20)[18]  # 95th percentile

    @property
    def p99_duration_ms(self) -> float:
        """99th percentile duration."""
        if len(self.durations) < 2:
            return self.durations[0] if self.durations else 0.0
        return statistics.quantiles(self.durations, n=100)[98]  # 99th percentile

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "call_count": self.call_count,
            "error_count": self.error_count,
            "error_rate_percent": round(self.error_rate, 2),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "p50_duration_ms": round(self.p50_duration_ms, 2),
            "p95_duration_ms": round(self.p95_duration_ms, 2),
            "p99_duration_ms": round(self.p99_duration_ms, 2),
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "last_call_time": self.last_call_time.isoformat() if self.last_call_time else None,
        }


class MetricsCollector:
    """Collects and aggregates metrics for the MCP server."""

    # Maximum number of duration samples to keep per tool
    MAX_DURATION_SAMPLES = 1000

    def __init__(self) -> None:
        self._lock = Lock()
        self._tool_metrics: dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self._start_time = datetime.now(timezone.utc)
        self._total_requests = 0
        self._total_errors = 0

        # Network metrics
        self._network_requests_by_domain: dict[str, int] = defaultdict(int)
        self._network_requests_by_type: dict[str, int] = defaultdict(int)
        self._network_errors = 0

        # Browser metrics
        self._browser_launches = 0
        self._browser_crashes = 0
        self._pages_created = 0
        self._pages_closed = 0

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record a tool call with its result."""
        with self._lock:
            self._total_requests += 1
            if not success:
                self._total_errors += 1

            metrics = self._tool_metrics[tool_name]
            metrics.call_count += 1
            metrics.total_duration_ms += duration_ms
            metrics.last_call_time = datetime.now(timezone.utc)

            # Keep duration samples for percentile calculations
            metrics.durations.append(duration_ms)
            if len(metrics.durations) > self.MAX_DURATION_SAMPLES:
                metrics.durations = metrics.durations[-self.MAX_DURATION_SAMPLES:]

            if not success:
                metrics.error_count += 1
                metrics.last_error = error
                metrics.last_error_time = datetime.now(timezone.utc)

    def record_network_request(self, domain: str, resource_type: str, success: bool) -> None:
        """Record a network request."""
        with self._lock:
            self._network_requests_by_domain[domain] += 1
            self._network_requests_by_type[resource_type] += 1
            if not success:
                self._network_errors += 1

    def record_browser_launch(self) -> None:
        """Record a browser launch."""
        with self._lock:
            self._browser_launches += 1

    def record_browser_crash(self) -> None:
        """Record a browser crash."""
        with self._lock:
            self._browser_crashes += 1

    def record_page_created(self) -> None:
        """Record a page creation."""
        with self._lock:
            self._pages_created += 1

    def record_page_closed(self) -> None:
        """Record a page close."""
        with self._lock:
            self._pages_closed += 1

    @property
    def uptime_seconds(self) -> float:
        """Server uptime in seconds."""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        with self._lock:
            # Sort tools by call count
            tool_metrics = {
                name: metrics.to_dict()
                for name, metrics in sorted(
                    self._tool_metrics.items(),
                    key=lambda x: x[1].call_count,
                    reverse=True,
                )
            }

            return {
                "server": {
                    "uptime_seconds": round(self.uptime_seconds, 2),
                    "start_time": self._start_time.isoformat(),
                    "total_requests": self._total_requests,
                    "total_errors": self._total_errors,
                    "error_rate_percent": round(
                        self._total_errors / self._total_requests * 100
                        if self._total_requests > 0
                        else 0,
                        2,
                    ),
                },
                "browser": {
                    "launches": self._browser_launches,
                    "crashes": self._browser_crashes,
                    "pages_created": self._pages_created,
                    "pages_closed": self._pages_closed,
                },
                "network": {
                    "requests_by_domain": dict(self._network_requests_by_domain),
                    "requests_by_type": dict(self._network_requests_by_type),
                    "errors": self._network_errors,
                },
                "tools": tool_metrics,
            }

    def get_tool_metrics(self, tool_name: str) -> dict[str, Any] | None:
        """Get metrics for a specific tool."""
        with self._lock:
            if tool_name in self._tool_metrics:
                return self._tool_metrics[tool_name].to_dict()
            return None

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._tool_metrics.clear()
            self._start_time = datetime.now(timezone.utc)
            self._total_requests = 0
            self._total_errors = 0
            self._network_requests_by_domain.clear()
            self._network_requests_by_type.clear()
            self._network_errors = 0
            self._browser_launches = 0
            self._browser_crashes = 0
            self._pages_created = 0
            self._pages_closed = 0


# Global metrics collector instance
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def reset_metrics() -> None:
    """Reset the global metrics collector."""
    global _metrics
    if _metrics:
        _metrics.reset()
