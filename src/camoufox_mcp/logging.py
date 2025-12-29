"""
Structured logging for Camoufox MCP Server.

Uses structlog for JSON-formatted logs suitable for production environments.
All logs go to stderr to avoid interfering with MCP stdio transport.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import Processor

from src.camoufox_mcp.config import get_config

# Context variables for request-scoped logging
tool_context: ContextVar[dict[str, Any]] = ContextVar("tool_context", default={})


def add_tool_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add tool context from contextvars to log entries."""
    ctx = tool_context.get()
    if ctx:
        event_dict.update(ctx)
    return event_dict


def sanitize_sensitive_data(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Remove sensitive data from logs (passwords, tokens, etc.)."""
    sensitive_keys = {"password", "token", "secret", "api_key", "auth", "cookie"}

    def sanitize(obj: Any, depth: int = 0) -> Any:
        if depth > 5:  # Prevent infinite recursion
            return obj
        if isinstance(obj, dict):
            return {
                k: "***REDACTED***" if any(s in k.lower() for s in sensitive_keys) else sanitize(v, depth + 1)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [sanitize(item, depth + 1) for item in obj]
        return obj

    return sanitize(event_dict)


def truncate_large_values(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Truncate large string values to prevent log bloat."""
    max_length = 1000

    def truncate(obj: Any, depth: int = 0) -> Any:
        if depth > 5:
            return obj
        if isinstance(obj, str) and len(obj) > max_length:
            return obj[:max_length] + f"... [truncated {len(obj) - max_length} chars]"
        if isinstance(obj, dict):
            return {k: truncate(v, depth + 1) for k, v in obj.items()}
        if isinstance(obj, list) and len(obj) > 20:
            return truncate(obj[:20], depth + 1) + [f"... [{len(obj) - 20} more items]"]
        if isinstance(obj, list):
            return [truncate(item, depth + 1) for item in obj]
        return obj

    return truncate(event_dict)


def configure_logging() -> None:
    """Configure structlog for the MCP server."""
    config = get_config()

    # Common processors for all formats
    common_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_tool_context,
        structlog.processors.add_log_level,
        sanitize_sensitive_data,
        truncate_large_values,
    ]

    if config.logging.include_timestamps:
        common_processors.append(
            structlog.processors.TimeStamper(fmt="iso", utc=True)
        )

    if config.logging.include_caller:
        common_processors.append(structlog.processors.CallsiteParameterAdder())

    common_processors.append(structlog.processors.StackInfoRenderer())
    common_processors.append(structlog.processors.UnicodeDecoder())

    # Format-specific final processor
    if config.logging.format == "json":
        final_processor: Processor = structlog.processors.JSONRenderer()
    else:
        final_processor = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.RichTracebackFormatter(),
        )

    common_processors.append(final_processor)

    # Configure structlog
    structlog.configure(
        processors=common_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.logging.level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, config.logging.level),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name or "camoufox_mcp")


def bind_tool_context(**kwargs: Any) -> None:
    """Bind context variables for the current tool call."""
    ctx = tool_context.get().copy()
    ctx.update(kwargs)
    tool_context.set(ctx)


def clear_tool_context() -> None:
    """Clear tool context after a tool call completes."""
    tool_context.set({})


# Initialize logging on import
_initialized = False


def ensure_logging_configured() -> None:
    """Ensure logging is configured (idempotent)."""
    global _initialized
    if not _initialized:
        configure_logging()
        _initialized = True
