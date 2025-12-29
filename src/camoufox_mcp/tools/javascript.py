"""
JavaScript evaluation tools for Camoufox MCP Server.

Tools: evaluate, evaluate_on_element
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector, validate_javascript

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register JavaScript evaluation tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(log_outputs=False)  # JS results can be large
    async def evaluate(
        expression: str,
        timeout: int | None = None,
    ) -> str:
        """
        Execute JavaScript in the page context.

        Args:
            expression: JavaScript expression or function to evaluate
            timeout: Evaluation timeout in milliseconds

        Returns:
            JSON-serialized result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Validate JavaScript
        valid, result = safe_validate(validate_javascript, expression)
        if not valid:
            return f"Error: Invalid JavaScript - {result}"

        config = get_config()
        eval_timeout = timeout or config.timeouts.js_evaluation

        try:
            result = await session.page.evaluate(expression, timeout=eval_timeout)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return f"Error evaluating JS: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def evaluate_on_element(
        selector: str,
        expression: str,
        timeout: int | None = None,
    ) -> str:
        """
        Execute JavaScript on a specific element.

        Args:
            selector: CSS selector for the element
            expression: JavaScript function receiving the element (e.g., "el => el.value")
            timeout: Evaluation timeout in milliseconds

        Returns:
            JSON-serialized result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Validate inputs
        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        valid, result = safe_validate(validate_javascript, expression)
        if not valid:
            return f"Error: Invalid JavaScript - {result}"

        config = get_config()
        eval_timeout = timeout or config.timeouts.js_evaluation

        try:
            result = await session.page.locator(selector).evaluate(
                expression, timeout=eval_timeout
            )
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return f"Error evaluating on element: {str(e)}"
