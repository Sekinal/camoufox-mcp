"""
Debug and inspection tools for Camoufox MCP Server.

Tools: get_browser_info, browser_health_check, get_session_metrics, reset_metrics
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.metrics import get_metrics
from src.camoufox_mcp.session import get_session

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register debug and inspection tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def get_browser_info() -> str:
        """
        Get information about the current browser session.

        Returns:
            JSON object with browser status, pages, and settings
        """
        session = get_session()
        info = session.get_info()
        return json.dumps(asdict(info), indent=2, default=str)

    @mcp.tool()
    @instrumented_tool()
    async def browser_health_check() -> str:
        """
        Check browser health and responsiveness.

        Performs a quick test to verify the browser is responding.

        Returns:
            JSON object with health status and diagnostics
        """
        session = get_session()
        health = await session.health_check()
        return json.dumps(health, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def browser_recover() -> str:
        """
        Attempt to recover from a browser crash or unresponsive state.

        This will close the current browser (if any) and launch a new one.
        If there was an active page, it will attempt to navigate back to
        the last URL.

        Returns:
            Recovery status message
        """
        session = get_session()
        return await session.recover()

    @mcp.tool()
    @instrumented_tool()
    async def get_session_metrics() -> str:
        """
        Get performance and usage metrics for the current session.

        Returns comprehensive metrics including:
        - Server uptime and request counts
        - Per-tool call counts, durations, and error rates
        - Browser launch/crash counts
        - Network request statistics

        Returns:
            JSON object with all metrics
        """
        metrics = get_metrics()
        return json.dumps(metrics.get_summary(), indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def get_tool_metrics(tool_name: str) -> str:
        """
        Get metrics for a specific tool.

        Args:
            tool_name: Name of the tool to get metrics for

        Returns:
            JSON object with tool-specific metrics
        """
        metrics = get_metrics()
        tool_metrics = metrics.get_tool_metrics(tool_name)

        if tool_metrics is None:
            return json.dumps({
                "error": f"No metrics found for tool '{tool_name}'",
                "available_tools": list(metrics._tool_metrics.keys()),
            }, indent=2)

        return json.dumps({
            "tool_name": tool_name,
            **tool_metrics,
        }, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def reset_metrics() -> str:
        """
        Reset all session metrics.

        This clears all collected metrics including tool call counts,
        error rates, and timing data. Useful for starting fresh measurements.

        Returns:
            Confirmation message
        """
        metrics = get_metrics()
        metrics.reset()
        return "All metrics have been reset."

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_page_errors() -> str:
        """
        Get JavaScript errors that occurred on the page.

        Returns:
            JSON array of page errors
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Set up error collection if not already done
        if not hasattr(session, "_page_errors"):
            session._page_errors = []

            def handle_error(error):
                session._page_errors.append({
                    "message": str(error),
                })

            session.page.on("pageerror", handle_error)
            return "Page error capture started. Call this tool again to retrieve errors."

        return json.dumps(session._page_errors, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def get_network_stats() -> str:
        """
        Get network request statistics from the session.

        Returns:
            JSON object with request counts by domain and resource type
        """
        session = get_session()
        metrics = get_metrics()

        return json.dumps({
            "network_log_size": len(session.network_log),
            "capture_enabled": session.capture_network,
            "capture_bodies": session.capture_bodies,
            "requests_by_domain": dict(metrics._network_requests_by_domain),
            "requests_by_type": dict(metrics._network_requests_by_type),
            "network_errors": metrics._network_errors,
        }, indent=2)
