"""
Browser management tools for Camoufox MCP Server.

Tools: launch_browser, close_browser, new_page, switch_page, list_pages, close_page
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_url

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register browser management tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(sensitive_params={"proxy_password"})
    async def launch_browser(
        headless: bool | None = None,
        proxy_server: str | None = None,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
        os_type: str = "random",
        humanize: bool | None = None,
        geoip: bool = False,
        block_images: bool = False,
        locale: str | None = None,
    ) -> str:
        """
        Launch a Camoufox browser with anti-detect capabilities.

        Args:
            headless: Run browser in headless mode (default from config)
            proxy_server: Proxy server URL (e.g., "http://proxy.example.com:8080")
            proxy_username: Proxy authentication username
            proxy_password: Proxy authentication password
            os_type: OS to spoof - "windows", "macos", "linux", or "random"
            humanize: Enable human-like cursor movement
            geoip: Auto-detect location from IP for geolocation spoofing
            block_images: Block image loading for faster scraping
            locale: Browser locale (e.g., "en-US")

        Returns:
            Status message about browser launch
        """
        session = get_session()

        proxy = None
        if proxy_server:
            proxy = {"server": proxy_server}
            if proxy_username:
                proxy["username"] = proxy_username
            if proxy_password:
                proxy["password"] = proxy_password

        os_setting = None if os_type == "random" else os_type

        return await session.launch(
            headless=headless,
            proxy=proxy,
            os_type=os_setting,
            humanize=humanize,
            geoip=geoip,
            block_images=block_images,
            locale=locale,
        )

    @mcp.tool()
    @instrumented_tool()
    async def close_browser() -> str:
        """
        Close the browser and clean up all resources.

        Returns:
            Confirmation message
        """
        session = get_session()
        return await session.close()

    @mcp.tool()
    @instrumented_tool()
    async def new_page(page_id: str = "new") -> str:
        """
        Create a new browser tab/page.

        Args:
            page_id: Identifier for this page (used to switch between pages)

        Returns:
            Status message
        """
        session = get_session()
        return await session.new_page(page_id)

    @mcp.tool()
    @instrumented_tool()
    async def switch_page(page_id: str) -> str:
        """
        Switch to a different page/tab.

        Args:
            page_id: The page identifier to switch to

        Returns:
            Status message
        """
        session = get_session()
        return await session.switch_page(page_id)

    @mcp.tool()
    @instrumented_tool()
    async def list_pages() -> str:
        """
        List all open pages/tabs.

        Returns:
            JSON list of page IDs and their URLs
        """
        session = get_session()

        if not session.pages:
            return "No pages open."

        pages_info = []
        for page_id, page in session.pages.items():
            try:
                url = page.url
            except Exception:
                url = "unknown"
            pages_info.append({
                "id": page_id,
                "url": url,
                "active": page_id == session._active_page_id,
            })

        return json.dumps(pages_info, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def close_page(page_id: str) -> str:
        """
        Close a specific page/tab.

        Args:
            page_id: The page identifier to close

        Returns:
            Status message
        """
        session = get_session()
        return await session.close_page(page_id)
