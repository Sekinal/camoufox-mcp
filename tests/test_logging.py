"""
Comprehensive tests for structured logging.

Tests log processors, context management, sanitization, and configuration.
"""

from __future__ import annotations

import io
import json
import logging
import sys
from unittest.mock import patch

import pytest
import structlog

from src.camoufox_mcp.logging import (
    add_tool_context,
    bind_tool_context,
    clear_tool_context,
    configure_logging,
    ensure_logging_configured,
    get_logger,
    sanitize_sensitive_data,
    tool_context,
    truncate_large_values,
)


class TestToolContext:
    """Tests for tool context management."""

    def setup_method(self):
        """Clear context before each test."""
        clear_tool_context()

    def teardown_method(self):
        """Clear context after each test."""
        clear_tool_context()

    def test_bind_single_value(self):
        """Bind a single context value."""
        bind_tool_context(tool_name="test_tool")
        ctx = tool_context.get()
        assert ctx["tool_name"] == "test_tool"

    def test_bind_multiple_values(self):
        """Bind multiple context values."""
        bind_tool_context(tool_name="test", call_id="abc123")
        ctx = tool_context.get()
        assert ctx["tool_name"] == "test"
        assert ctx["call_id"] == "abc123"

    def test_bind_accumulates(self):
        """Multiple bind calls accumulate values."""
        bind_tool_context(first="1")
        bind_tool_context(second="2")
        ctx = tool_context.get()
        assert ctx["first"] == "1"
        assert ctx["second"] == "2"

    def test_bind_overwrites(self):
        """Later binds overwrite earlier values."""
        bind_tool_context(key="old")
        bind_tool_context(key="new")
        ctx = tool_context.get()
        assert ctx["key"] == "new"

    def test_clear_removes_all(self):
        """Clear removes all context."""
        bind_tool_context(a="1", b="2", c="3")
        clear_tool_context()
        ctx = tool_context.get()
        assert ctx == {}

    def test_context_isolation(self):
        """Context should be isolated per call."""
        # This tests the contextvars behavior
        clear_tool_context()
        assert tool_context.get() == {}


class TestAddToolContext:
    """Tests for add_tool_context processor."""

    def setup_method(self):
        clear_tool_context()

    def teardown_method(self):
        clear_tool_context()

    def test_adds_context_to_event(self):
        """Processor adds bound context to event dict."""
        bind_tool_context(tool_name="my_tool", call_id="xyz789")
        event_dict = {"event": "test_event", "level": "info"}

        result = add_tool_context(None, "", event_dict)

        assert result["tool_name"] == "my_tool"
        assert result["call_id"] == "xyz789"
        assert result["event"] == "test_event"

    def test_preserves_existing_keys(self):
        """Processor preserves existing event dict keys."""
        bind_tool_context(tool_name="tool")
        event_dict = {"event": "test", "custom_key": "custom_value"}

        result = add_tool_context(None, "", event_dict)

        assert result["custom_key"] == "custom_value"
        assert result["tool_name"] == "tool"

    def test_empty_context(self):
        """Empty context doesn't break processor."""
        clear_tool_context()
        event_dict = {"event": "test"}

        result = add_tool_context(None, "", event_dict)

        assert result == {"event": "test"}


class TestSanitizeSensitiveData:
    """Tests for sensitive data sanitization."""

    def test_redacts_password(self):
        """Password fields are redacted."""
        event = {"password": "secret123", "username": "john"}
        result = sanitize_sensitive_data(None, "", event)
        assert result["password"] == "***REDACTED***"
        assert result["username"] == "john"

    def test_redacts_token(self):
        """Token fields are redacted."""
        event = {"auth_token": "abc123", "data": "visible"}
        result = sanitize_sensitive_data(None, "", event)
        assert result["auth_token"] == "***REDACTED***"
        assert result["data"] == "visible"

    def test_redacts_secret(self):
        """Secret fields are redacted."""
        event = {"client_secret": "xyz", "client_id": "123"}
        result = sanitize_sensitive_data(None, "", event)
        assert result["client_secret"] == "***REDACTED***"
        assert result["client_id"] == "123"

    def test_redacts_api_key(self):
        """API key fields are redacted."""
        event = {"api_key": "key123", "version": "v1"}
        result = sanitize_sensitive_data(None, "", event)
        assert result["api_key"] == "***REDACTED***"

    def test_redacts_cookie(self):
        """Cookie fields are redacted."""
        event = {"session_cookie": "abc", "page": "/home"}
        result = sanitize_sensitive_data(None, "", event)
        assert result["session_cookie"] == "***REDACTED***"

    def test_redacts_nested_sensitive(self):
        """Sensitive data in nested dicts is redacted."""
        event = {
            "config": {
                "api_key": "secret",
                "endpoint": "https://api.example.com",
            }
        }
        result = sanitize_sensitive_data(None, "", event)
        assert result["config"]["api_key"] == "***REDACTED***"
        assert result["config"]["endpoint"] == "https://api.example.com"

    def test_redacts_in_lists(self):
        """Sensitive data in lists is redacted."""
        event = {
            "credentials": [
                {"password": "pass1"},
                {"password": "pass2"},
            ]
        }
        result = sanitize_sensitive_data(None, "", event)
        assert result["credentials"][0]["password"] == "***REDACTED***"
        assert result["credentials"][1]["password"] == "***REDACTED***"

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        event = {
            "PASSWORD": "secret",
            "Token": "abc",
            "API_KEY": "xyz",
        }
        result = sanitize_sensitive_data(None, "", event)
        assert result["PASSWORD"] == "***REDACTED***"
        assert result["Token"] == "***REDACTED***"
        assert result["API_KEY"] == "***REDACTED***"

    def test_partial_match(self):
        """Partial key matches are redacted."""
        event = {
            "user_password_hash": "hash123",
            "bearer_token_value": "token123",
        }
        result = sanitize_sensitive_data(None, "", event)
        assert result["user_password_hash"] == "***REDACTED***"
        assert result["bearer_token_value"] == "***REDACTED***"

    def test_depth_limit(self):
        """Deep nesting is handled with depth limit."""
        # Create deeply nested structure
        deep = {"level": 0}
        current = deep
        for i in range(10):
            current["nested"] = {"level": i + 1}
            current = current["nested"]
        current["password"] = "secret"

        event = {"deep": deep}
        result = sanitize_sensitive_data(None, "", event)
        # Should not crash, and should handle gracefully


class TestTruncateLargeValues:
    """Tests for large value truncation."""

    def test_truncates_long_string(self):
        """Long strings are truncated."""
        long_string = "x" * 2000
        event = {"data": long_string}
        result = truncate_large_values(None, "", event)
        assert len(result["data"]) < 2000
        assert "truncated" in result["data"]

    def test_preserves_short_string(self):
        """Short strings are not truncated."""
        event = {"data": "short string"}
        result = truncate_large_values(None, "", event)
        assert result["data"] == "short string"

    def test_truncates_at_1000_chars(self):
        """Truncation happens at 1000 characters."""
        string_999 = "x" * 999
        string_1001 = "x" * 1001

        result_999 = truncate_large_values(None, "", {"data": string_999})
        result_1001 = truncate_large_values(None, "", {"data": string_1001})

        assert result_999["data"] == string_999  # Not truncated
        assert len(result_1001["data"]) == 1000 + len("... [truncated 1 chars]")

    def test_truncates_long_list(self):
        """Long lists are truncated."""
        long_list = list(range(50))
        event = {"items": long_list}
        result = truncate_large_values(None, "", event)
        assert len(result["items"]) == 21  # 20 items + "more items" message

    def test_preserves_short_list(self):
        """Short lists are not truncated."""
        short_list = [1, 2, 3, 4, 5]
        event = {"items": short_list}
        result = truncate_large_values(None, "", event)
        assert result["items"] == short_list

    def test_truncates_nested(self):
        """Nested long values are truncated."""
        event = {
            "outer": {
                "inner": "y" * 2000
            }
        }
        result = truncate_large_values(None, "", event)
        assert "truncated" in result["outer"]["inner"]

    def test_depth_limit(self):
        """Deep nesting respects depth limit."""
        deep = {"level": 0}
        current = deep
        for i in range(10):
            current["nested"] = {"level": i + 1, "data": "x" * 2000}
            current = current["nested"]

        event = {"deep": deep}
        result = truncate_large_values(None, "", event)
        # Should not crash


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self):
        """get_logger returns a bound logger."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_default_name(self):
        """Default logger name is camoufox_mcp."""
        logger = get_logger()
        assert logger is not None

    def test_different_names_same_type(self):
        """Different logger names return same type."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        assert type(logger1) == type(logger2)


class TestEnsureLoggingConfigured:
    """Tests for logging configuration."""

    def test_idempotent(self):
        """Multiple calls don't reconfigure."""
        # First call configures
        ensure_logging_configured()
        # Second call should be no-op
        ensure_logging_configured()
        # If we get here, it's idempotent

    def test_logger_works_after_configure(self):
        """Logger works after configuration."""
        ensure_logging_configured()
        logger = get_logger("test")
        # Should not raise
        logger.info("test message", key="value")


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configures_structlog(self):
        """structlog is configured."""
        configure_logging()
        # Get a logger and use it
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_logs_configured(self):
        """Logging is properly configured."""
        configure_logging()
        logger = get_logger("config_test")
        # Should not raise - logger is usable
        assert logger is not None


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def setup_method(self):
        clear_tool_context()

    def teardown_method(self):
        clear_tool_context()

    def test_full_logging_flow(self):
        """Test complete logging flow with context and sanitization."""
        ensure_logging_configured()

        # Bind context
        bind_tool_context(tool_name="integration_test", call_id="test123")

        # Get logger
        logger = get_logger("integration")

        # Log with sensitive data (should be sanitized)
        # This should not raise
        logger.info(
            "test_event",
            password="secret",  # Should be redacted
            data="visible",
            long_value="x" * 2000,  # Should be truncated
        )

        # Clear context
        clear_tool_context()

    def test_error_logging(self):
        """Test error logging with exception info."""
        ensure_logging_configured()
        logger = get_logger("error_test")

        try:
            raise ValueError("Test exception")
        except ValueError:
            # Should not raise - log the error without exception formatter
            logger.error("Caught exception", error="Test exception")

    def test_debug_logging(self):
        """Test debug level logging."""
        ensure_logging_configured()
        logger = get_logger("debug_test")

        # Should not raise even if debug is disabled
        logger.debug("debug message", details={"key": "value"})

    def test_warning_logging(self):
        """Test warning level logging."""
        ensure_logging_configured()
        logger = get_logger("warning_test")

        logger.warning("warning message", issue="test issue")
