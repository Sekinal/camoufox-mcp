"""
Tests for metrics collection.
"""

import time

import pytest

from src.camoufox_mcp.metrics import MetricsCollector, get_metrics, reset_metrics


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def setup_method(self):
        """Reset metrics before each test."""
        reset_metrics()

    def test_record_tool_call_success(self):
        """Test recording a successful tool call."""
        collector = MetricsCollector()

        collector.record_tool_call("test_tool", 100.0, success=True)

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics is not None
        assert metrics["call_count"] == 1
        assert metrics["error_count"] == 0
        assert metrics["avg_duration_ms"] == 100.0

    def test_record_tool_call_failure(self):
        """Test recording a failed tool call."""
        collector = MetricsCollector()

        collector.record_tool_call("test_tool", 50.0, success=False, error="Test error")

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics is not None
        assert metrics["call_count"] == 1
        assert metrics["error_count"] == 1
        assert metrics["last_error"] == "Test error"

    def test_multiple_calls(self):
        """Test recording multiple calls."""
        collector = MetricsCollector()

        collector.record_tool_call("test_tool", 100.0, success=True)
        collector.record_tool_call("test_tool", 200.0, success=True)
        collector.record_tool_call("test_tool", 300.0, success=False, error="Error")

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics["call_count"] == 3
        assert metrics["error_count"] == 1
        assert metrics["avg_duration_ms"] == 200.0  # (100 + 200 + 300) / 3

    def test_error_rate(self):
        """Test error rate calculation."""
        collector = MetricsCollector()

        # 2 successes, 2 failures = 50% error rate
        collector.record_tool_call("test_tool", 100.0, success=True)
        collector.record_tool_call("test_tool", 100.0, success=True)
        collector.record_tool_call("test_tool", 100.0, success=False)
        collector.record_tool_call("test_tool", 100.0, success=False)

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics["error_rate_percent"] == 50.0

    def test_get_summary(self):
        """Test getting full metrics summary."""
        collector = MetricsCollector()

        collector.record_tool_call("tool1", 100.0, success=True)
        collector.record_tool_call("tool2", 200.0, success=True)
        collector.record_browser_launch()

        summary = collector.get_summary()

        assert "server" in summary
        assert "browser" in summary
        assert "tools" in summary
        assert summary["browser"]["launches"] == 1
        assert "tool1" in summary["tools"]
        assert "tool2" in summary["tools"]

    def test_uptime(self):
        """Test uptime calculation."""
        collector = MetricsCollector()

        time.sleep(0.1)  # Wait 100ms
        uptime = collector.uptime_seconds

        assert uptime >= 0.1

    def test_network_metrics(self):
        """Test network request metrics."""
        collector = MetricsCollector()

        collector.record_network_request("example.com", "document", True)
        collector.record_network_request("example.com", "script", True)
        collector.record_network_request("cdn.example.com", "image", False)

        summary = collector.get_summary()

        assert summary["network"]["requests_by_domain"]["example.com"] == 2
        assert summary["network"]["requests_by_type"]["document"] == 1
        assert summary["network"]["errors"] == 1

    def test_browser_metrics(self):
        """Test browser metrics."""
        collector = MetricsCollector()

        collector.record_browser_launch()
        collector.record_page_created()
        collector.record_page_created()
        collector.record_page_closed()
        collector.record_browser_crash()

        summary = collector.get_summary()

        assert summary["browser"]["launches"] == 1
        assert summary["browser"]["crashes"] == 1
        assert summary["browser"]["pages_created"] == 2
        assert summary["browser"]["pages_closed"] == 1

    def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()

        collector.record_tool_call("test_tool", 100.0, success=True)
        collector.reset()

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics is None

    def test_get_metrics_singleton(self):
        """Test get_metrics returns same instance."""
        reset_metrics()
        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2


class TestToolMetrics:
    """Tests for individual tool metrics."""

    def test_percentiles_single_value(self):
        """Test percentiles with single value."""
        collector = MetricsCollector()

        collector.record_tool_call("test", 100.0, success=True)

        metrics = collector.get_tool_metrics("test")
        assert metrics["p50_duration_ms"] == 100.0
        assert metrics["p95_duration_ms"] == 100.0

    def test_percentiles_multiple_values(self):
        """Test percentiles with multiple values."""
        collector = MetricsCollector()

        # Add 100 values from 1 to 100
        for i in range(1, 101):
            collector.record_tool_call("test", float(i), success=True)

        metrics = collector.get_tool_metrics("test")

        # Median should be around 50
        assert 45 <= metrics["p50_duration_ms"] <= 55

        # p95 should be around 95
        assert 90 <= metrics["p95_duration_ms"] <= 100
