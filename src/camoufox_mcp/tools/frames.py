"""
Frame and dialog handling tools for Camoufox MCP Server.

Tools: list_frames, frame_locator, handle_dialog, get_console_logs
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register frame and dialog handling tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def list_frames() -> str:
        """
        List all frames in the current page.

        Returns:
            JSON array of frames with name and URL
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        frames = []
        for frame in session.page.frames:
            frames.append({
                "name": frame.name,
                "url": frame.url,
                "is_main": frame == session.page.main_frame,
            })
        return json.dumps(frames, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def frame_locator(
        frame_selector: str,
        element_selector: str,
        action: Literal["click", "fill", "get_text", "get_html"] = "click",
        fill_value: str | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Interact with an element inside an iframe.

        Args:
            frame_selector: Selector for the iframe element
            element_selector: Selector for the element inside the frame
            action: Action to perform - "click", "fill", "get_text", or "get_html"
            fill_value: Value to fill (required for "fill" action)
            timeout: Action timeout in milliseconds

        Returns:
            Action result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Validate selectors
        valid, result = safe_validate(validate_selector, frame_selector)
        if not valid:
            return f"Error: Invalid frame selector - {result}"

        valid, result = safe_validate(validate_selector, element_selector)
        if not valid:
            return f"Error: Invalid element selector - {result}"

        if action == "fill" and fill_value is None:
            return "Error: fill_value is required for 'fill' action."

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            frame = session.page.frame_locator(frame_selector)
            locator = frame.locator(element_selector)

            if action == "click":
                await locator.click(timeout=action_timeout)
                return "Clicked element in frame."
            elif action == "fill":
                await locator.fill(fill_value, timeout=action_timeout)
                return "Filled element in frame."
            elif action == "get_text":
                return await locator.inner_text(timeout=action_timeout)
            elif action == "get_html":
                return await locator.inner_html(timeout=action_timeout)
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error with frame: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def handle_dialog(
        action: Literal["accept", "dismiss"] = "accept",
        prompt_text: str | None = None,
    ) -> str:
        """
        Set up automatic handling for dialogs (alert, confirm, prompt).

        Args:
            action: How to handle dialogs - "accept" or "dismiss"
            prompt_text: Text to enter for prompt dialogs

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        async def dialog_handler(dialog):
            if action == "accept":
                if prompt_text and dialog.type == "prompt":
                    await dialog.accept(prompt_text)
                else:
                    await dialog.accept()
            else:
                await dialog.dismiss()

        # Remove previous handlers and add new one
        session.page.on("dialog", dialog_handler)

        return (
            f"Dialog handler set: {action}"
            + (f" with text '{prompt_text}'" if prompt_text else "")
        )

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_console_logs(clear: bool = False) -> str:
        """
        Get console logs from the page.

        Note: This returns logs captured since the handler was set up.
        Call this tool once to start capturing, then call again to retrieve logs.

        Args:
            clear: Clear captured logs after returning them

        Returns:
            JSON array of console messages
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Use a simple approach - capture logs in the page context
        try:
            # Check if we already have a log handler set up
            if not hasattr(session, "_console_logs"):
                session._console_logs = []

                def handle_console(msg):
                    session._console_logs.append({
                        "type": msg.type,
                        "text": msg.text,
                        "location": str(msg.location) if msg.location else None,
                    })

                session.page.on("console", handle_console)
                return "Console log capture started. Call this tool again to retrieve captured logs."

            logs = session._console_logs.copy()

            if clear:
                session._console_logs.clear()

            return json.dumps(logs, indent=2)

        except Exception as e:
            return f"Error with console logs: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def frame_by_name(frame_name: str) -> str:
        """
        Get information about a frame by its name.

        Args:
            frame_name: Name of the frame to find

        Returns:
            Frame information or error message
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            frame = session.page.frame(name=frame_name)
            if frame:
                return json.dumps({
                    "name": frame.name,
                    "url": frame.url,
                    "found": True,
                }, indent=2)
            else:
                return json.dumps({
                    "found": False,
                    "error": f"Frame '{frame_name}' not found",
                }, indent=2)
        except Exception as e:
            return f"Error finding frame: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def frame_by_url(url_pattern: str) -> str:
        """
        Get information about a frame by URL pattern.

        Args:
            url_pattern: URL substring or pattern to match

        Returns:
            Frame information or error message
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            frame = session.page.frame(url=lambda url: url_pattern in url)
            if frame:
                return json.dumps({
                    "name": frame.name,
                    "url": frame.url,
                    "found": True,
                }, indent=2)
            else:
                return json.dumps({
                    "found": False,
                    "error": f"Frame matching '{url_pattern}' not found",
                }, indent=2)
        except Exception as e:
            return f"Error finding frame: {str(e)}"
