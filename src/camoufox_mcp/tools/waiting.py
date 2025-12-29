"""
Wait and timing tools for Camoufox MCP Server.

Tools: wait_for_selector, wait_for_load_state, wait
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector, validate_timeout

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register wait and timing tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def wait_for_selector(
        selector: str,
        state: Literal["attached", "detached", "visible", "hidden"] = "visible",
        timeout: int | None = None,
    ) -> str:
        """
        Wait for an element to reach a specific state.

        Args:
            selector: CSS selector to wait for
            state: Target state - "attached", "detached", "visible", or "hidden"
            timeout: Maximum wait time in milliseconds

        Returns:
            Success or timeout message
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Validate selector
        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        wait_timeout = timeout or config.timeouts.selector_wait

        try:
            await session.page.wait_for_selector(
                selector, state=state, timeout=wait_timeout
            )
            return f"Element '{selector}' is now {state}."
        except Exception as e:
            return f"Timeout waiting for '{selector}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def wait_for_load_state(
        state: Literal["load", "domcontentloaded", "networkidle"] = "load",
        timeout: int | None = None,
    ) -> str:
        """
        Wait for the page to reach a load state.

        Args:
            state: Load state - "load", "domcontentloaded", or "networkidle"
            timeout: Maximum wait time in milliseconds

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        wait_timeout = timeout or config.timeouts.navigation

        try:
            await session.page.wait_for_load_state(state, timeout=wait_timeout)
            return f"Page reached '{state}' state."
        except Exception as e:
            return f"Timeout waiting for '{state}' state: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def wait(milliseconds: int) -> str:
        """
        Wait for a specified duration.

        Args:
            milliseconds: Time to wait in milliseconds (max 60000)

        Returns:
            Confirmation
        """
        # Validate timeout (max 60 seconds)
        if milliseconds < 0:
            return "Error: Wait time cannot be negative."
        if milliseconds > 60000:
            return "Error: Wait time cannot exceed 60000ms (1 minute)."

        await asyncio.sleep(milliseconds / 1000)
        return f"Waited {milliseconds}ms."

    @mcp.tool()
    @instrumented_tool()
    async def wait_for_url(
        url_pattern: str,
        timeout: int | None = None,
    ) -> str:
        """
        Wait for the page URL to match a pattern.

        Args:
            url_pattern: URL substring or regex pattern to match
            timeout: Maximum wait time in milliseconds

        Returns:
            Success message with final URL
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        wait_timeout = timeout or config.timeouts.navigation

        try:
            await session.page.wait_for_url(url_pattern, timeout=wait_timeout)
            return f"URL matched pattern. Current URL: {session.page.url}"
        except Exception as e:
            return f"Timeout waiting for URL pattern '{url_pattern}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def wait_for_function(
        expression: str,
        timeout: int | None = None,
    ) -> str:
        """
        Wait for a JavaScript function to return truthy value.

        Args:
            expression: JavaScript expression that returns a truthy value when ready
            timeout: Maximum wait time in milliseconds

        Returns:
            Success message or timeout
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        wait_timeout = timeout or config.timeouts.js_evaluation

        try:
            await session.page.wait_for_function(expression, timeout=wait_timeout)
            return "Function returned truthy value."
        except Exception as e:
            return f"Timeout waiting for function: {str(e)}"
