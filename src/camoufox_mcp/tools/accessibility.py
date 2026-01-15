"""
Accessibility tools for Camoufox MCP Server.

Provides accessibility tree snapshots for LLM-friendly page understanding.

Tools: get_accessibility_snapshot
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register accessibility tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_accessibility_snapshot(
        interesting_only: bool = True,
        root_selector: str | None = None,
    ) -> str:
        """
        Capture accessibility snapshot of the current page.

        Returns a structured representation of the page's accessibility tree,
        which is more useful for LLMs than raw HTML. The snapshot includes
        element roles, names, values, and states.

        Args:
            interesting_only: If True, only include interesting/interactive elements
                             (buttons, links, inputs, etc.). Default is True.
            root_selector: Optional CSS selector to limit snapshot to a subtree

        Returns:
            JSON string containing the accessibility tree snapshot
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            import json

            # Get the accessibility snapshot
            if root_selector:
                element = session.page.locator(root_selector)
                snapshot = await element.aria_snapshot()
            else:
                snapshot = await session.page.accessibility.snapshot(
                    interesting_only=interesting_only
                )

            if not snapshot:
                return "Error: Could not capture accessibility snapshot. Page may not have loaded."

            # Format the snapshot nicely
            def format_node(node: dict, indent: int = 0) -> str:
                """Format accessibility node for readability."""
                lines = []
                prefix = "  " * indent

                role = node.get("role", "")
                name = node.get("name", "")
                value = node.get("value", "")

                # Build node description
                parts = [f"[{role}]"]
                if name:
                    parts.append(f'"{name}"')
                if value:
                    parts.append(f"value={value}")

                # Add relevant states
                for key in ["checked", "disabled", "expanded", "pressed", "selected", "readonly"]:
                    if node.get(key):
                        parts.append(f"{key}={node[key]}")

                lines.append(f"{prefix}{' '.join(parts)}")

                # Process children
                children = node.get("children", [])
                for child in children:
                    lines.append(format_node(child, indent + 1))

                return "\n".join(lines)

            formatted = format_node(snapshot)

            # Also include the raw JSON for programmatic access
            result = {
                "formatted": formatted,
                "raw": snapshot,
                "url": session.page.url,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error capturing accessibility snapshot: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_aria_snapshot(
        selector: str | None = None,
    ) -> str:
        """
        Get ARIA snapshot as a YAML-like string representation.

        This provides a compact, readable representation of the accessibility
        tree that's particularly useful for understanding page structure.

        Args:
            selector: Optional CSS selector to limit snapshot to a subtree.
                     If not provided, returns snapshot of the entire page.

        Returns:
            YAML-like string representation of the accessibility tree
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            if selector:
                element = session.page.locator(selector)
                snapshot = await element.aria_snapshot()
            else:
                # Get root snapshot
                snapshot = await session.page.locator("body").aria_snapshot()

            return snapshot

        except Exception as e:
            return f"Error getting ARIA snapshot: {str(e)}"
