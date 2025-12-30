"""
Compound action tools for Camoufox MCP Server.

These tools combine multiple actions into single calls to reduce token usage.
Tools: batch_actions, fill_form, click_text, fill_by_label
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register compound action tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def batch_actions(actions: list[dict[str, Any]]) -> str:
        """
        Execute multiple actions in sequence. Stops on first error.

        Args:
            actions: List of action objects. Each action has:
                - action: "click", "fill", "type", "press", "select", "check", "uncheck", "hover", "wait"
                - selector: CSS/XPath selector (required for most actions)
                - value: Value for fill/type/select actions
                - key: Key for press action
                - ms: Milliseconds for wait action

        Example:
            [
                {"action": "fill", "selector": "#username", "value": "john"},
                {"action": "fill", "selector": "#password", "value": "secret"},
                {"action": "click", "selector": "button[type=submit]"}
            ]

        Returns:
            Summary of executed actions or error details
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if not actions:
            return "Error: No actions provided."

        config = get_config()
        timeout = config.timeouts.element_action
        results = []

        for i, action_def in enumerate(actions):
            action_type = action_def.get("action", "").lower()
            selector = action_def.get("selector")
            value = action_def.get("value")

            try:
                if action_type == "click":
                    if not selector:
                        return f"Error at action {i}: click requires selector"
                    await session.page.click(selector, timeout=timeout)
                    results.append(f"clicked {selector}")

                elif action_type == "fill":
                    if not selector or value is None:
                        return f"Error at action {i}: fill requires selector and value"
                    await session.page.fill(selector, str(value), timeout=timeout)
                    results.append(f"filled {selector}")

                elif action_type == "type":
                    if not selector or value is None:
                        return f"Error at action {i}: type requires selector and value"
                    delay = action_def.get("delay", 50)
                    await session.page.type(selector, str(value), delay=delay, timeout=timeout)
                    results.append(f"typed into {selector}")

                elif action_type == "press":
                    key = action_def.get("key")
                    if not key:
                        return f"Error at action {i}: press requires key"
                    if selector:
                        await session.page.press(selector, key, timeout=timeout)
                    else:
                        await session.page.keyboard.press(key)
                    results.append(f"pressed {key}")

                elif action_type == "select":
                    if not selector:
                        return f"Error at action {i}: select requires selector"
                    if value is not None:
                        await session.page.select_option(selector, value=str(value), timeout=timeout)
                    elif action_def.get("label"):
                        await session.page.select_option(
                            selector, label=action_def["label"], timeout=timeout
                        )
                    elif action_def.get("index") is not None:
                        await session.page.select_option(
                            selector, index=action_def["index"], timeout=timeout
                        )
                    else:
                        return f"Error at action {i}: select requires value, label, or index"
                    results.append(f"selected in {selector}")

                elif action_type == "check":
                    if not selector:
                        return f"Error at action {i}: check requires selector"
                    await session.page.check(selector, timeout=timeout)
                    results.append(f"checked {selector}")

                elif action_type == "uncheck":
                    if not selector:
                        return f"Error at action {i}: uncheck requires selector"
                    await session.page.uncheck(selector, timeout=timeout)
                    results.append(f"unchecked {selector}")

                elif action_type == "hover":
                    if not selector:
                        return f"Error at action {i}: hover requires selector"
                    await session.page.hover(selector, timeout=timeout)
                    results.append(f"hovered {selector}")

                elif action_type == "wait":
                    ms = action_def.get("ms", 1000)
                    await session.page.wait_for_timeout(ms)
                    results.append(f"waited {ms}ms")

                elif action_type == "wait_for":
                    if not selector:
                        return f"Error at action {i}: wait_for requires selector"
                    state = action_def.get("state", "visible")
                    await session.page.wait_for_selector(selector, state=state, timeout=timeout)
                    results.append(f"waited for {selector}")

                else:
                    return f"Error at action {i}: unknown action '{action_type}'"

            except Exception as e:
                return f"Error at action {i} ({action_type}): {str(e)}"

        return f"Completed {len(results)} actions: " + ", ".join(results)

    @mcp.tool()
    @instrumented_tool()
    async def fill_form(
        fields: dict[str, str],
        submit_selector: str | None = None,
    ) -> str:
        """
        Fill multiple form fields at once, optionally submit.

        Args:
            fields: Dictionary mapping selectors to values.
                    Example: {"#username": "john", "#email": "john@example.com"}
            submit_selector: Optional selector for submit button to click after filling

        Returns:
            Summary of filled fields
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if not fields:
            return "Error: No fields provided."

        config = get_config()
        timeout = config.timeouts.element_action
        filled = []

        for selector, value in fields.items():
            valid, result = safe_validate(validate_selector, selector)
            if not valid:
                return f"Error: Invalid selector '{selector}' - {result}"

            try:
                await session.page.fill(selector, str(value), timeout=timeout)
                filled.append(selector)
            except Exception as e:
                return f"Error filling '{selector}': {str(e)}"

        result_msg = f"Filled {len(filled)} fields"

        if submit_selector:
            try:
                await session.page.click(submit_selector, timeout=timeout)
                result_msg += f", clicked {submit_selector}"
            except Exception as e:
                return f"{result_msg}, but error clicking submit: {str(e)}"

        return result_msg

    @mcp.tool()
    @instrumented_tool()
    async def click_text(
        text: str,
        exact: bool = False,
        tag: str | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Click an element by its text content. No selector needed.

        Args:
            text: Text to find and click
            exact: If True, match exact text. If False, match partial text.
            tag: Optional tag name to filter (e.g., "button", "a", "span")
            timeout: Action timeout in milliseconds

        Returns:
            Click result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            if tag:
                if exact:
                    locator = session.page.locator(f"{tag}:text-is('{text}')")
                else:
                    locator = session.page.locator(f"{tag}:has-text('{text}')")
            else:
                if exact:
                    locator = session.page.get_by_text(text, exact=True)
                else:
                    locator = session.page.get_by_text(text)

            await locator.first.click(timeout=action_timeout)
            return f"Clicked element with text: '{text}'"
        except Exception as e:
            return f"Error clicking text '{text}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def fill_by_label(
        label: str,
        value: str,
        exact: bool = False,
        timeout: int | None = None,
    ) -> str:
        """
        Find an input by its label text and fill it. No selector needed.

        Args:
            label: Label text associated with the input
            value: Value to fill
            exact: If True, match exact label text
            timeout: Action timeout in milliseconds

        Returns:
            Fill result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            locator = session.page.get_by_label(label, exact=exact)
            await locator.fill(value, timeout=action_timeout)
            return f"Filled input labeled '{label}'"
        except Exception as e:
            return f"Error filling by label '{label}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def click_role(
        role: str,
        name: str | None = None,
        exact: bool = False,
        timeout: int | None = None,
    ) -> str:
        """
        Click an element by its ARIA role. No selector needed.

        Args:
            role: ARIA role (button, link, textbox, checkbox, menuitem, tab, etc.)
            name: Accessible name to match (button text, link text, etc.)
            exact: If True, match exact name
            timeout: Action timeout in milliseconds

        Returns:
            Click result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            if name:
                locator = session.page.get_by_role(role, name=name, exact=exact)
            else:
                locator = session.page.get_by_role(role)
            await locator.first.click(timeout=action_timeout)
            desc = f"role={role}" + (f", name='{name}'" if name else "")
            return f"Clicked element with {desc}"
        except Exception as e:
            return f"Error clicking role '{role}': {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def fill_placeholder(
        placeholder: str,
        value: str,
        exact: bool = False,
        timeout: int | None = None,
    ) -> str:
        """
        Find an input by its placeholder text and fill it. No selector needed.

        Args:
            placeholder: Placeholder text of the input
            value: Value to fill
            exact: If True, match exact placeholder text
            timeout: Action timeout in milliseconds

        Returns:
            Fill result
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            locator = session.page.get_by_placeholder(placeholder, exact=exact)
            await locator.fill(value, timeout=action_timeout)
            return f"Filled input with placeholder '{placeholder}'"
        except Exception as e:
            return f"Error filling by placeholder '{placeholder}': {str(e)}"
