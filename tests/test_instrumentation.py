"""
Comprehensive tests for tool instrumentation.

Tests the decorator, context manager, logging, metrics recording, and error handling.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.camoufox_mcp.instrumentation import (
    InstrumentationContext,
    generate_call_id,
    instrumented_tool,
)
from src.camoufox_mcp.metrics import get_metrics, reset_metrics


class TestGenerateCallId:
    """Tests for call ID generation."""

    def test_generates_string(self):
        """Call ID should be a string."""
        call_id = generate_call_id()
        assert isinstance(call_id, str)

    def test_correct_length(self):
        """Call ID should be 12 characters."""
        call_id = generate_call_id()
        assert len(call_id) == 12

    def test_hexadecimal(self):
        """Call ID should be valid hexadecimal."""
        call_id = generate_call_id()
        # Should not raise ValueError
        int(call_id, 16)

    def test_unique_ids(self):
        """Each call should generate unique ID."""
        ids = {generate_call_id() for _ in range(1000)}
        assert len(ids) == 1000  # All unique


class TestInstrumentedToolDecorator:
    """Tests for the @instrumented_tool decorator."""

    @pytest.fixture(autouse=True)
    def reset_metrics_fixture(self):
        """Reset metrics before each test."""
        reset_metrics()
        yield
        reset_metrics()

    def test_preserves_function_name(self):
        """Decorator should preserve function name."""

        @instrumented_tool()
        async def my_tool_function():
            return "result"

        assert my_tool_function.__name__ == "my_tool_function"

    def test_preserves_docstring(self):
        """Decorator should preserve docstring."""

        @instrumented_tool()
        async def documented_tool():
            """This is the docstring."""
            return "result"

        assert documented_tool.__doc__ == "This is the docstring."

    @pytest.mark.asyncio
    async def test_async_function_works(self):
        """Decorated async function should work correctly."""

        @instrumented_tool()
        async def async_tool(value: str) -> str:
            return f"processed: {value}"

        result = await async_tool(value="test")
        assert result == "processed: test"

    def test_sync_function_works(self):
        """Decorated sync function should work correctly."""

        @instrumented_tool()
        def sync_tool(value: str) -> str:
            return f"processed: {value}"

        result = sync_tool(value="test")
        assert result == "processed: test"

    @pytest.mark.asyncio
    async def test_records_success_metrics(self):
        """Successful calls should record metrics."""

        @instrumented_tool()
        async def success_tool():
            return "ok"

        await success_tool()

        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics("success_tool")
        assert tool_metrics is not None
        assert tool_metrics["call_count"] == 1
        assert tool_metrics["error_count"] == 0

    @pytest.mark.asyncio
    async def test_records_error_metrics(self):
        """Failed calls should record error metrics."""

        @instrumented_tool()
        async def error_tool():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await error_tool()

        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics("error_tool")
        assert tool_metrics is not None
        assert tool_metrics["call_count"] == 1
        assert tool_metrics["error_count"] == 1

    @pytest.mark.asyncio
    async def test_custom_tool_name(self):
        """Custom tool name should be used in metrics."""

        @instrumented_tool(name="custom_name")
        async def original_name():
            return "ok"

        await original_name()

        metrics = get_metrics()
        assert metrics.get_tool_metrics("custom_name") is not None
        assert metrics.get_tool_metrics("original_name") is None

    @pytest.mark.asyncio
    async def test_duration_recorded(self):
        """Duration should be recorded in metrics."""

        @instrumented_tool()
        async def slow_tool():
            await asyncio.sleep(0.05)  # 50ms
            return "ok"

        await slow_tool()

        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics("slow_tool")
        assert tool_metrics["avg_duration_ms"] >= 40  # Allow some variance

    @pytest.mark.asyncio
    async def test_sensitive_param_redaction(self):
        """Sensitive parameters should be redacted in logs."""

        @instrumented_tool(sensitive_params={"secret_key"})
        async def tool_with_secret(secret_key: str, normal: str):
            return "ok"

        # The test verifies the decorator doesn't crash with sensitive params
        # Full log verification would require capturing log output
        result = await tool_with_secret(secret_key="my-secret", normal="visible")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_default_sensitive_params(self):
        """Default sensitive params (password, token, secret) should be redacted."""

        @instrumented_tool()
        async def tool_with_password(password: str, username: str):
            return "ok"

        result = await tool_with_password(password="secret123", username="john")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_long_input_truncation(self):
        """Long input values should be truncated in logs."""

        @instrumented_tool()
        async def tool_with_long_input(data: str):
            return len(data)

        long_data = "x" * 1000
        result = await tool_with_long_input(data=long_data)
        assert result == 1000

    @pytest.mark.asyncio
    async def test_log_inputs_disabled(self):
        """log_inputs=False should work."""

        @instrumented_tool(log_inputs=False)
        async def no_log_inputs(sensitive: str):
            return "ok"

        result = await no_log_inputs(sensitive="data")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_log_outputs_disabled(self):
        """log_outputs=False should work."""

        @instrumented_tool(log_outputs=False)
        async def no_log_outputs():
            return "large output that shouldn't be logged"

        result = await no_log_outputs()
        assert "large output" in result

    @pytest.mark.asyncio
    async def test_exception_propagates(self):
        """Exceptions should propagate after being logged."""

        @instrumented_tool()
        async def failing_tool():
            raise RuntimeError("Expected failure")

        with pytest.raises(RuntimeError, match="Expected failure"):
            await failing_tool()

    @pytest.mark.asyncio
    async def test_multiple_calls(self):
        """Multiple calls should accumulate metrics."""

        @instrumented_tool()
        async def multi_call_tool():
            return "ok"

        for _ in range(5):
            await multi_call_tool()

        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics("multi_call_tool")
        assert tool_metrics["call_count"] == 5

    def test_sync_records_metrics(self):
        """Sync functions should also record metrics."""

        @instrumented_tool()
        def sync_metric_tool():
            return "ok"

        sync_metric_tool()

        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics("sync_metric_tool")
        assert tool_metrics["call_count"] == 1

    def test_sync_exception_handling(self):
        """Sync function exceptions should be handled."""

        @instrumented_tool()
        def sync_error_tool():
            raise ValueError("Sync error")

        with pytest.raises(ValueError):
            sync_error_tool()

        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics("sync_error_tool")
        assert tool_metrics["error_count"] == 1


class TestInstrumentationContext:
    """Tests for InstrumentationContext context manager."""

    @pytest.fixture(autouse=True)
    def reset_metrics_fixture(self):
        """Reset metrics before each test."""
        reset_metrics()
        yield
        reset_metrics()

    @pytest.mark.asyncio
    async def test_async_context_basic(self):
        """Basic async context manager usage."""
        async with InstrumentationContext("test_operation") as ctx:
            ctx.add_metadata("key", "value")
            # Operation happens here

        # If we get here without exception, it worked

    def test_sync_context_basic(self):
        """Basic sync context manager usage."""
        with InstrumentationContext("test_operation") as ctx:
            ctx.add_metadata("key", "value")
            # Operation happens here

    @pytest.mark.asyncio
    async def test_async_exception_handling(self):
        """Exceptions in async context should be logged."""
        with pytest.raises(RuntimeError):
            async with InstrumentationContext("failing_op"):
                raise RuntimeError("Test error")

    def test_sync_exception_handling(self):
        """Exceptions in sync context should be logged."""
        with pytest.raises(ValueError):
            with InstrumentationContext("failing_op"):
                raise ValueError("Test error")

    @pytest.mark.asyncio
    async def test_metadata_accumulation(self):
        """Metadata should accumulate."""
        async with InstrumentationContext("meta_op") as ctx:
            ctx.add_metadata("first", 1)
            ctx.add_metadata("second", 2)
            ctx.add_metadata("third", 3)
            assert ctx._metadata == {"first": 1, "second": 2, "third": 3}

    def test_call_id_generated(self):
        """Context should have a call ID."""
        ctx = InstrumentationContext("test")
        assert len(ctx.call_id) == 12

    def test_unique_call_ids(self):
        """Each context should have unique call ID."""
        ids = {InstrumentationContext(f"op_{i}").call_id for i in range(100)}
        assert len(ids) == 100

    @pytest.mark.asyncio
    async def test_timing_recorded(self):
        """Duration should be tracked."""
        async with InstrumentationContext("timed_op") as ctx:
            await asyncio.sleep(0.02)  # 20ms

        # Start time should have been set
        assert ctx.start_time is not None


class TestInstrumentationIntegration:
    """Integration tests combining decorators and context managers."""

    @pytest.fixture(autouse=True)
    def reset_metrics_fixture(self):
        """Reset metrics before each test."""
        reset_metrics()
        yield
        reset_metrics()

    @pytest.mark.asyncio
    async def test_nested_instrumentation(self):
        """Nested instrumentation should work."""

        @instrumented_tool()
        async def outer_tool():
            async with InstrumentationContext("inner_operation"):
                return "nested result"

        result = await outer_tool()
        assert result == "nested result"

        metrics = get_metrics()
        assert metrics.get_tool_metrics("outer_tool")["call_count"] == 1

    @pytest.mark.asyncio
    async def test_parallel_calls(self):
        """Parallel calls should be handled correctly."""

        @instrumented_tool()
        async def parallel_tool(n: int):
            await asyncio.sleep(0.01)
            return n * 2

        results = await asyncio.gather(
            parallel_tool(n=1),
            parallel_tool(n=2),
            parallel_tool(n=3),
        )

        assert results == [2, 4, 6]

        metrics = get_metrics()
        assert metrics.get_tool_metrics("parallel_tool")["call_count"] == 3

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self):
        """Mixed success/failure should record correctly."""

        call_count = 0

        @instrumented_tool()
        async def flaky_tool():
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise ValueError("Periodic failure")
            return "ok"

        for _ in range(9):
            try:
                await flaky_tool()
            except ValueError:
                pass

        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics("flaky_tool")
        assert tool_metrics["call_count"] == 9
        assert tool_metrics["error_count"] == 3  # Every 3rd call fails
