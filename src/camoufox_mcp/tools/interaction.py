"""
Page interaction tools for Camoufox MCP Server.

Tools: click, fill, type_text, press_key, select_option, check, uncheck, hover, scroll, upload_file, drag_and_drop
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector, validate_file_path

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register page interaction tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def click(
        selector: str,
        button: Literal["left", "right", "middle"] = "left",
        click_count: int = 1,
        delay: int = 0,
        timeout: int | None = None,
    ) -> str:
        """
        Click an element on the page.

        Args:
            selector: CSS selector, XPath (starting with //), or text selector
            button: Mouse button - "left", "right", or "middle"
            click_count: Number of clicks (2 for double-click)
            delay: Delay between mousedown and mouseup in milliseconds
            timeout: Action timeout in milliseconds

        Returns:
            Click result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        # Validate selector
        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            await session.page.click(
                selector,
                button=button,
                click_count=click_count,
                delay=delay,
                timeout=action_timeout,
            )
            return f"Clicked element: {selector}"
        except Exception as e:
            return f"Error clicking '{selector}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def fill(
        selector: str,
        value: str,
        timeout: int | None = None,
    ) -> str:
        """
        Fill a text input or textarea with a value.

        Args:
            selector: CSS selector for the input element
            value: Text to fill in
            timeout: Action timeout in milliseconds

        Returns:
            Fill result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            await session.page.fill(selector, value, timeout=action_timeout)
            return f"Filled '{selector}' with value."
        except Exception as e:
            return f"Error filling '{selector}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def type_text(
        selector: str,
        text: str,
        delay: int = 50,
        timeout: int | None = None,
    ) -> str:
        """
        Type text character by character (more human-like than fill).

        Args:
            selector: CSS selector for the input element
            text: Text to type
            delay: Delay between keystrokes in milliseconds
            timeout: Action timeout in milliseconds

        Returns:
            Type result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            await session.page.type(selector, text, delay=delay, timeout=action_timeout)
            return f"Typed text into '{selector}'."
        except Exception as e:
            return f"Error typing into '{selector}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def press_key(
        key: str,
        selector: str | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Press a keyboard key.

        Args:
            key: Key to press (e.g., "Enter", "Tab", "Escape", "ArrowDown", "Control+a")
            selector: Optional selector to focus first
            timeout: Action timeout in milliseconds

        Returns:
            Key press result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if selector:
            valid, result = safe_validate(validate_selector, selector)
            if not valid:
                return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            if selector:
                await session.page.press(selector, key, timeout=action_timeout)
            else:
                await session.page.keyboard.press(key)
            return f"Pressed key: {key}"
        except Exception as e:
            return f"Error pressing key '{key}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def select_option(
        selector: str,
        value: str | None = None,
        label: str | None = None,
        index: int | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Select an option from a dropdown/select element.

        Args:
            selector: CSS selector for the select element
            value: Option value to select
            label: Option label/text to select
            index: Option index to select (0-based)
            timeout: Action timeout in milliseconds

        Returns:
            Selection result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            if value is not None:
                await session.page.select_option(selector, value=value, timeout=action_timeout)
            elif label is not None:
                await session.page.select_option(selector, label=label, timeout=action_timeout)
            elif index is not None:
                await session.page.select_option(selector, index=index, timeout=action_timeout)
            else:
                return "Error: Must provide value, label, or index."
            return f"Selected option in '{selector}'."
        except Exception as e:
            return f"Error selecting option: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def check(selector: str, timeout: int | None = None) -> str:
        """
        Check a checkbox or radio button.

        Args:
            selector: CSS selector for the checkbox/radio
            timeout: Action timeout in milliseconds

        Returns:
            Check result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            await session.page.check(selector, timeout=action_timeout)
            return f"Checked: {selector}"
        except Exception as e:
            return f"Error checking '{selector}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def uncheck(selector: str, timeout: int | None = None) -> str:
        """
        Uncheck a checkbox.

        Args:
            selector: CSS selector for the checkbox
            timeout: Action timeout in milliseconds

        Returns:
            Uncheck result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            await session.page.uncheck(selector, timeout=action_timeout)
            return f"Unchecked: {selector}"
        except Exception as e:
            return f"Error unchecking '{selector}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def hover(selector: str, timeout: int | None = None) -> str:
        """
        Hover over an element.

        Args:
            selector: CSS selector for the element
            timeout: Action timeout in milliseconds

        Returns:
            Hover result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            await session.page.hover(selector, timeout=action_timeout)
            return f"Hovering over: {selector}"
        except Exception as e:
            return f"Error hovering '{selector}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def scroll(
        x: int = 0,
        y: int = 0,
        selector: str | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Scroll the page or an element.

        Args:
            x: Horizontal scroll amount in pixels
            y: Vertical scroll amount in pixels (positive = down)
            selector: Optional element to scroll into view instead
            timeout: Action timeout in milliseconds

        Returns:
            Scroll result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if selector:
            valid, result = safe_validate(validate_selector, selector)
            if not valid:
                return f"Error: Invalid selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            if selector:
                await session.page.locator(selector).scroll_into_view_if_needed(timeout=action_timeout)
                return f"Scrolled '{selector}' into view."
            else:
                await session.page.evaluate(f"window.scrollBy({x}, {y})")
                return f"Scrolled by ({x}, {y})."
        except Exception as e:
            return f"Error scrolling: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def upload_file(
        selector: str,
        file_path: str,
        timeout: int | None = None,
    ) -> str:
        """
        Upload a file to a file input.

        Args:
            selector: CSS selector for the file input
            file_path: Path to the file to upload
            timeout: Action timeout in milliseconds

        Returns:
            Upload result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        valid, result = safe_validate(validate_file_path, file_path, must_exist=True)
        if not valid:
            return f"Error: Invalid file path - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            await session.page.set_input_files(selector, file_path, timeout=action_timeout)
            return f"Uploaded file to '{selector}'."
        except Exception as e:
            return f"Error uploading file: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def drag_and_drop(
        source_selector: str,
        target_selector: str,
        source_position: dict | None = None,
        target_position: dict | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Perform drag and drop between two elements.

        Args:
            source_selector: CSS selector for the source element to drag
            target_selector: CSS selector for the target element to drop onto
            source_position: Optional position within source element {"x": int, "y": int}
            target_position: Optional position within target element {"x": int, "y": int}
            timeout: Action timeout in milliseconds

        Returns:
            Drag and drop result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, source_selector)
        if not valid:
            return f"Error: Invalid source selector - {result}"

        valid, result = safe_validate(validate_selector, target_selector)
        if not valid:
            return f"Error: Invalid target selector - {result}"

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            source = session.page.locator(source_selector)
            target = session.page.locator(target_selector)

            # Build options dict
            options = {"timeout": action_timeout}
            if source_position:
                options["source_position"] = source_position
            if target_position:
                options["target_position"] = target_position

            await source.drag_to(target, **options)
            return f"Dragged '{source_selector}' to '{target_selector}'."
        except Exception as e:
            return f"Error during drag and drop: {str(e)}"
