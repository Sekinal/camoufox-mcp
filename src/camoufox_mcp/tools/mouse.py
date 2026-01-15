"""
Coordinate-based mouse interaction tools for Camoufox MCP Server.

These tools provide low-level mouse control using screen coordinates,
useful for vision-based automation and complex interactions.

Tools: mouse_move_xy, mouse_click_xy, mouse_drag_xy, mouse_wheel
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register coordinate-based mouse tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def mouse_move_xy(
        x: int,
        y: int,
        steps: int = 1,
    ) -> str:
        """
        Move mouse to a given position.

        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
            steps: Number of intermediate steps for the movement (more = smoother)

        Returns:
            Move result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.mouse.move(x, y, steps=steps)
            return f"Mouse moved to ({x}, {y})."
        except Exception as e:
            return f"Error moving mouse: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def mouse_click_xy(
        x: int,
        y: int,
        button: Literal["left", "right", "middle"] = "left",
        click_count: int = 1,
        delay: int = 0,
    ) -> str:
        """
        Click left mouse button at a given position.

        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
            button: Mouse button to click ("left", "right", or "middle")
            click_count: Number of clicks (2 for double-click)
            delay: Delay between mousedown and mouseup in milliseconds

        Returns:
            Click result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.mouse.click(
                x, y,
                button=button,
                click_count=click_count,
                delay=delay,
            )
            action = "Double-clicked" if click_count == 2 else "Clicked"
            return f"{action} at ({x}, {y}) with {button} button."
        except Exception as e:
            return f"Error clicking: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def mouse_drag_xy(
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        steps: int = 5,
    ) -> str:
        """
        Drag left mouse button from one position to another.

        Performs a drag operation by pressing at start position,
        moving to end position, and releasing.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            steps: Number of intermediate steps for smoother movement

        Returns:
            Drag result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            # Move to start position
            await session.page.mouse.move(start_x, start_y)
            # Press mouse button
            await session.page.mouse.down()
            # Move to end position
            await session.page.mouse.move(end_x, end_y, steps=steps)
            # Release mouse button
            await session.page.mouse.up()

            return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."
        except Exception as e:
            return f"Error dragging: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def mouse_wheel(
        delta_x: int = 0,
        delta_y: int = 0,
    ) -> str:
        """
        Dispatch a mouse wheel event.

        Args:
            delta_x: Horizontal scroll delta (positive = right)
            delta_y: Vertical scroll delta (positive = down)

        Returns:
            Wheel result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.mouse.wheel(delta_x, delta_y)
            return f"Mouse wheel scrolled by ({delta_x}, {delta_y})."
        except Exception as e:
            return f"Error scrolling wheel: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def mouse_down(
        button: Literal["left", "right", "middle"] = "left",
        click_count: int = 1,
    ) -> str:
        """
        Press and hold a mouse button.

        Args:
            button: Mouse button to press ("left", "right", or "middle")
            click_count: Number of clicks to simulate

        Returns:
            Press result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.mouse.down(button=button, click_count=click_count)
            return f"Mouse {button} button pressed."
        except Exception as e:
            return f"Error pressing mouse button: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def mouse_up(
        button: Literal["left", "right", "middle"] = "left",
        click_count: int = 1,
    ) -> str:
        """
        Release a mouse button.

        Args:
            button: Mouse button to release ("left", "right", or "middle")
            click_count: Number of clicks to simulate

        Returns:
            Release result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.mouse.up(button=button, click_count=click_count)
            return f"Mouse {button} button released."
        except Exception as e:
            return f"Error releasing mouse button: {str(e)}"
