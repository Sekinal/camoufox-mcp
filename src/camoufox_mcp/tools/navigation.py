"""
Navigation tools for Camoufox MCP Server.

Tools: goto, reload, go_back, go_forward, get_url, get_page_title
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_url

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register navigation tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def goto(
        url: str,
        wait_until: Literal["load", "domcontentloaded", "networkidle", "commit"] = "load",
        timeout: int | None = None,
    ) -> str:
        """
        Navigate to a URL.

        Args:
            url: The URL to navigate to
            wait_until: When to consider navigation complete - "load", "domcontentloaded", "networkidle", or "commit"
            timeout: Navigation timeout in milliseconds (default from config)

        Returns:
            Navigation result with final URL and status
        """
        session = get_session()

        if not session.page:
            return json.dumps({"success": False, "error": "No active page. Launch browser first."})

        # Validate URL
        valid, result = safe_validate(validate_url, url)
        if not valid:
            return json.dumps({"success": False, "error": f"Invalid URL: {result}"})

        config = get_config()
        nav_timeout = timeout or config.timeouts.navigation

        try:
            response = await session.page.goto(url, wait_until=wait_until, timeout=nav_timeout)
            status = response.status if response else "unknown"
            final_url = session.page.url
            return json.dumps({
                "success": True,
                "status": status,
                "url": final_url,
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    @instrumented_tool()
    async def reload(
        wait_until: Literal["load", "domcontentloaded", "networkidle", "commit"] = "load",
        timeout: int | None = None,
    ) -> str:
        """
        Reload the current page.

        Args:
            wait_until: When to consider reload complete
            timeout: Reload timeout in milliseconds (default from config)

        Returns:
            Reload result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        nav_timeout = timeout or config.timeouts.navigation

        try:
            await session.page.reload(wait_until=wait_until, timeout=nav_timeout)
            return f"Page reloaded. URL: {session.page.url}"
        except Exception as e:
            return f"Error reloading page: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def go_back(timeout: int | None = None) -> str:
        """
        Navigate back in history.

        Args:
            timeout: Navigation timeout in milliseconds

        Returns:
            Navigation result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        nav_timeout = timeout or config.timeouts.navigation

        try:
            await session.page.go_back(timeout=nav_timeout)
            return f"Navigated back. URL: {session.page.url}"
        except Exception as e:
            return f"Error navigating back: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def go_forward(timeout: int | None = None) -> str:
        """
        Navigate forward in history.

        Args:
            timeout: Navigation timeout in milliseconds

        Returns:
            Navigation result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        nav_timeout = timeout or config.timeouts.navigation

        try:
            await session.page.go_forward(timeout=nav_timeout)
            return f"Navigated forward. URL: {session.page.url}"
        except Exception as e:
            return f"Error navigating forward: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def get_url() -> str:
        """
        Get the current page URL.

        Returns:
            Current URL
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        return session.page.url

    @mcp.tool()
    @instrumented_tool()
    async def get_page_title() -> str:
        """
        Get the page title.

        Returns:
            Page title
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            return await session.page.title()
        except Exception as e:
            return f"Error getting title: {str(e)}"
