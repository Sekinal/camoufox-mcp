"""
PDF generation tools for Camoufox MCP Server.

Tools: save_as_pdf
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


def register(mcp: FastMCP) -> None:
    """Register PDF tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def save_as_pdf(
        path: str | None = None,
        scale: float = 1.0,
        display_header_footer: bool = False,
        header_template: str | None = None,
        footer_template: str | None = None,
        print_background: bool = True,
        landscape: bool = False,
        page_ranges: str | None = None,
        format: str | None = None,
        width: str | None = None,
        height: str | None = None,
        margin_top: str | None = None,
        margin_bottom: str | None = None,
        margin_left: str | None = None,
        margin_right: str | None = None,
        prefer_css_page_size: bool = False,
    ) -> str:
        """
        Save the current page as a PDF.

        Note: PDF generation only works in headless mode in Chromium-based browsers.
        Camoufox uses Firefox which has limited PDF support - this may not work
        in all configurations.

        Args:
            path: File path to save PDF (if None, saves to default directory)
            scale: Scale of the PDF rendering (default: 1.0)
            display_header_footer: Display header and footer
            header_template: HTML template for header
            footer_template: HTML template for footer
            print_background: Print background graphics (default: True)
            landscape: Landscape orientation (default: False)
            page_ranges: Page ranges (e.g., "1-5, 8, 11-13")
            format: Paper format (e.g., "Letter", "A4")
            width: Paper width (e.g., "8.5in")
            height: Paper height (e.g., "11in")
            margin_top: Top margin (e.g., "1cm")
            margin_bottom: Bottom margin
            margin_left: Left margin
            margin_right: Right margin
            prefer_css_page_size: Prefer page size defined by CSS

        Returns:
            Path to saved PDF file
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            config = get_config()

            # Determine output path
            if path is None:
                # Generate default path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = config.paths.screenshot_dir
                os.makedirs(output_dir, exist_ok=True)
                path = os.path.join(output_dir, f"page_{timestamp}.pdf")
            else:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

            # Build options dict
            options = {
                "path": path,
                "scale": scale,
                "display_header_footer": display_header_footer,
                "print_background": print_background,
                "landscape": landscape,
                "prefer_css_page_size": prefer_css_page_size,
            }

            if header_template:
                options["header_template"] = header_template
            if footer_template:
                options["footer_template"] = footer_template
            if page_ranges:
                options["page_ranges"] = page_ranges
            if format:
                options["format"] = format
            if width:
                options["width"] = width
            if height:
                options["height"] = height

            # Add margins if specified
            margin = {}
            if margin_top:
                margin["top"] = margin_top
            if margin_bottom:
                margin["bottom"] = margin_bottom
            if margin_left:
                margin["left"] = margin_left
            if margin_right:
                margin["right"] = margin_right
            if margin:
                options["margin"] = margin

            await session.page.pdf(**options)

            return f"PDF saved to: {path}"

        except Exception as e:
            error_msg = str(e)
            if "pdf" in error_msg.lower() and "headless" in error_msg.lower():
                return "Error: PDF generation requires headless mode. Please relaunch browser with headless=True."
            return f"Error saving PDF: {error_msg}"
