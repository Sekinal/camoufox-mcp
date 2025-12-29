"""
Screenshot and viewport tools for Camoufox MCP Server.

Tools: screenshot, get_viewport_size, set_viewport_size
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import TYPE_CHECKING

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector, validate_viewport

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register screenshot and viewport tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(log_outputs=False)  # Base64 is huge
    async def screenshot(
        path: str | None = None,
        full_page: bool = False,
        selector: str | None = None,
        quality: int | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Take a screenshot of the page or an element.

        Args:
            path: File path to save screenshot (if None, returns base64)
            full_page: Capture the full scrollable page
            selector: CSS selector to screenshot specific element
            quality: JPEG quality 0-100 (only for JPEG format)
            timeout: Action timeout in milliseconds

        Returns:
            Path to saved file or base64-encoded image
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if selector:
            valid, result = safe_validate(validate_selector, selector)
            if not valid:
                return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.screenshot

        try:
            screenshot_kwargs = {}

            # Determine format from path extension
            if path:
                path_obj = Path(path)
                if path_obj.suffix.lower() in (".jpg", ".jpeg"):
                    screenshot_kwargs["type"] = "jpeg"
                    if quality:
                        screenshot_kwargs["quality"] = max(0, min(100, quality))

            if selector:
                screenshot_bytes = await session.page.locator(selector).screenshot(
                    timeout=action_timeout, **screenshot_kwargs
                )
            else:
                screenshot_bytes = await session.page.screenshot(
                    full_page=full_page, timeout=action_timeout, **screenshot_kwargs
                )

            if path:
                path_obj = Path(path)
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(screenshot_bytes)
                return f"Screenshot saved to: {path}"
            else:
                b64 = base64.b64encode(screenshot_bytes).decode()
                return f"data:image/png;base64,{b64}"

        except Exception as e:
            return f"Error taking screenshot: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def get_viewport_size() -> str:
        """
        Get the current viewport size.

        Returns:
            JSON object with width and height
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        size = session.page.viewport_size
        return json.dumps(size)

    @mcp.tool()
    @instrumented_tool()
    async def set_viewport_size(width: int, height: int) -> str:
        """
        Set the viewport size.

        Args:
            width: Viewport width in pixels
            height: Viewport height in pixels

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Validate viewport dimensions
        valid, result = safe_validate(validate_viewport, width, height)
        if not valid:
            return f"Error: Invalid viewport - {result}"

        try:
            await session.page.set_viewport_size({"width": width, "height": height})
            return f"Viewport set to {width}x{height}."
        except Exception as e:
            return f"Error setting viewport: {str(e)}"
