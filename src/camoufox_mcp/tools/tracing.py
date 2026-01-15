"""
Tracing tools for Camoufox MCP Server.

Provides trace recording for debugging and analysis.

Tools: start_tracing, stop_tracing
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


# Track tracing state
_tracing_active = False


def register(mcp: FastMCP) -> None:
    """Register tracing tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def start_tracing(
        name: str | None = None,
        screenshots: bool = True,
        snapshots: bool = True,
        sources: bool = False,
    ) -> str:
        """
        Start trace recording.

        Records all browser actions, network requests, and optionally
        screenshots/snapshots for later analysis. The trace can be
        viewed in the Playwright Trace Viewer.

        Args:
            name: Optional name for the trace
            screenshots: Capture screenshots during tracing (default: True)
            snapshots: Capture DOM snapshots (default: True)
            sources: Include source files in trace (default: False)

        Returns:
            Status message
        """
        global _tracing_active

        session = get_session()

        if not session.browser:
            return "Error: Browser not launched. Call launch_browser first."

        if _tracing_active:
            return "Error: Tracing already active. Stop current trace first with stop_tracing."

        try:
            # Get the browser context
            # Since camoufox creates pages directly, we need to get context from page
            if not session.page:
                return "Error: No active page."

            context = session.page.context

            await context.tracing.start(
                name=name,
                screenshots=screenshots,
                snapshots=snapshots,
                sources=sources,
            )

            _tracing_active = True

            return f"Trace recording started" + (f" (name: {name})" if name else "") + "."

        except Exception as e:
            return f"Error starting trace: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def stop_tracing(
        path: str | None = None,
    ) -> str:
        """
        Stop trace recording and save the trace file.

        The trace file can be viewed with:
        - Playwright CLI: npx playwright show-trace trace.zip
        - Online: https://trace.playwright.dev

        Args:
            path: File path to save trace (if None, saves to default directory)

        Returns:
            Path to saved trace file
        """
        global _tracing_active

        session = get_session()

        if not session.page:
            return "Error: No active page."

        if not _tracing_active:
            return "Error: No active trace recording. Start one with start_tracing."

        try:
            config = get_config()

            # Determine output path
            if path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = config.paths.screenshot_dir
                os.makedirs(output_dir, exist_ok=True)
                path = os.path.join(output_dir, f"trace_{timestamp}.zip")
            else:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

            context = session.page.context
            await context.tracing.stop(path=path)

            _tracing_active = False

            return f"Trace saved to: {path}\nView with: npx playwright show-trace {path}"

        except Exception as e:
            _tracing_active = False
            return f"Error stopping trace: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def tracing_status() -> str:
        """
        Check the current tracing status.

        Returns:
            Current tracing state
        """
        if _tracing_active:
            return "Tracing is active."
        else:
            return "Tracing is not active."
