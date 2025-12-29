"""
Tool instrumentation for Camoufox MCP Server.

Provides decorators and utilities for automatic logging, metrics, and error handling.
"""

from __future__ import annotations

import asyncio
import functools
import time
import traceback
import uuid
from typing import Any, Callable, ParamSpec, TypeVar

from src.camoufox_mcp.logging import bind_tool_context, clear_tool_context, get_logger
from src.camoufox_mcp.metrics import get_metrics

P = ParamSpec("P")
T = TypeVar("T")


def generate_call_id() -> str:
    """Generate a unique ID for a tool call."""
    return uuid.uuid4().hex[:12]


def instrumented_tool(
    name: str | None = None,
    log_inputs: bool = True,
    log_outputs: bool = True,
    sensitive_params: set[str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that adds instrumentation to a tool function.

    Automatically:
    - Generates unique call IDs
    - Logs tool entry and exit with timing
    - Records metrics (call count, duration, errors)
    - Captures errors with full context
    - Binds context for structured logging

    Args:
        name: Tool name (defaults to function name)
        log_inputs: Whether to log input parameters
        log_outputs: Whether to log output (may be large)
        sensitive_params: Parameter names to redact from logs
    """
    sensitive = sensitive_params or {"password", "token", "secret", "proxy_password"}

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        tool_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            call_id = generate_call_id()
            logger = get_logger(tool_name)
            metrics = get_metrics()
            start_time = time.perf_counter()

            # Bind context for this call
            bind_tool_context(
                tool_name=tool_name,
                call_id=call_id,
            )

            # Prepare sanitized inputs for logging
            sanitized_kwargs = {}
            if log_inputs:
                for k, v in kwargs.items():
                    if k in sensitive:
                        sanitized_kwargs[k] = "***REDACTED***"
                    elif isinstance(v, str) and len(v) > 200:
                        sanitized_kwargs[k] = v[:200] + "..."
                    else:
                        sanitized_kwargs[k] = v

            logger.info(
                "tool_call_start",
                inputs=sanitized_kwargs if log_inputs else None,
            )

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log success
                output_preview = None
                if log_outputs and result is not None:
                    result_str = str(result)
                    output_preview = result_str[:500] if len(result_str) > 500 else result_str

                logger.info(
                    "tool_call_success",
                    duration_ms=round(duration_ms, 2),
                    output_preview=output_preview,
                )

                # Record metrics
                metrics.record_tool_call(tool_name, duration_ms, success=True)

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = str(e)
                error_type = type(e).__name__

                # Log error with stack trace
                logger.error(
                    "tool_call_error",
                    duration_ms=round(duration_ms, 2),
                    error=error_msg,
                    error_type=error_type,
                    traceback=traceback.format_exc(),
                )

                # Record metrics
                metrics.record_tool_call(
                    tool_name, duration_ms, success=False, error=error_msg
                )

                raise

            finally:
                clear_tool_context()

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            call_id = generate_call_id()
            logger = get_logger(tool_name)
            metrics = get_metrics()
            start_time = time.perf_counter()

            # Bind context for this call
            bind_tool_context(
                tool_name=tool_name,
                call_id=call_id,
            )

            # Prepare sanitized inputs for logging
            sanitized_kwargs = {}
            if log_inputs:
                for k, v in kwargs.items():
                    if k in sensitive:
                        sanitized_kwargs[k] = "***REDACTED***"
                    elif isinstance(v, str) and len(v) > 200:
                        sanitized_kwargs[k] = v[:200] + "..."
                    else:
                        sanitized_kwargs[k] = v

            logger.info(
                "tool_call_start",
                inputs=sanitized_kwargs if log_inputs else None,
            )

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log success
                output_preview = None
                if log_outputs and result is not None:
                    result_str = str(result)
                    output_preview = result_str[:500] if len(result_str) > 500 else result_str

                logger.info(
                    "tool_call_success",
                    duration_ms=round(duration_ms, 2),
                    output_preview=output_preview,
                )

                # Record metrics
                metrics.record_tool_call(tool_name, duration_ms, success=True)

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = str(e)
                error_type = type(e).__name__

                # Log error with stack trace
                logger.error(
                    "tool_call_error",
                    duration_ms=round(duration_ms, 2),
                    error=error_msg,
                    error_type=error_type,
                    traceback=traceback.format_exc(),
                )

                # Record metrics
                metrics.record_tool_call(
                    tool_name, duration_ms, success=False, error=error_msg
                )

                raise

            finally:
                clear_tool_context()

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


class InstrumentationContext:
    """
    Context manager for manual instrumentation of code blocks.

    Usage:
        async with InstrumentationContext("my_operation") as ctx:
            # Do work here
            ctx.add_metadata("key", "value")
    """

    def __init__(self, operation_name: str) -> None:
        self.operation_name = operation_name
        self.call_id = generate_call_id()
        self.logger = get_logger(operation_name)
        self.metrics = get_metrics()
        self.start_time: float | None = None
        self._metadata: dict[str, Any] = {}

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the operation context."""
        self._metadata[key] = value

    async def __aenter__(self) -> InstrumentationContext:
        self.start_time = time.perf_counter()
        bind_tool_context(
            operation=self.operation_name,
            call_id=self.call_id,
        )
        self.logger.debug("operation_start", **self._metadata)
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000 if self.start_time else 0

        if exc_val:
            self.logger.error(
                "operation_error",
                duration_ms=round(duration_ms, 2),
                error=str(exc_val),
                error_type=exc_type.__name__ if exc_type else None,
                **self._metadata,
            )
        else:
            self.logger.debug(
                "operation_complete",
                duration_ms=round(duration_ms, 2),
                **self._metadata,
            )

        clear_tool_context()

    def __enter__(self) -> InstrumentationContext:
        self.start_time = time.perf_counter()
        bind_tool_context(
            operation=self.operation_name,
            call_id=self.call_id,
        )
        self.logger.debug("operation_start", **self._metadata)
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000 if self.start_time else 0

        if exc_val:
            self.logger.error(
                "operation_error",
                duration_ms=round(duration_ms, 2),
                error=str(exc_val),
                error_type=exc_type.__name__ if exc_type else None,
                **self._metadata,
            )
        else:
            self.logger.debug(
                "operation_complete",
                duration_ms=round(duration_ms, 2),
                **self._metadata,
            )

        clear_tool_context()
