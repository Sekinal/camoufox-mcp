"""
Content extraction tools for Camoufox MCP Server.

Tools: get_text, get_html, get_attribute, query_selector_all, inspect_element
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
    """Register content extraction tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(log_outputs=False)  # Can be large
    async def get_text(selector: str | None = None, timeout: int | None = None) -> str:
        """
        Get text content from an element or the entire page.

        Args:
            selector: CSS selector (if None, gets all page text)
            timeout: Action timeout in milliseconds

        Returns:
            Text content
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
                return await session.page.locator(selector).inner_text(timeout=action_timeout)
            else:
                return await session.page.locator("body").inner_text(timeout=action_timeout)
        except Exception as e:
            return f"Error getting text: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)  # HTML can be very large
    async def get_html(
        selector: str | None = None,
        outer: bool = True,
        timeout: int | None = None,
    ) -> str:
        """
        Get HTML content from an element or the entire page.

        Args:
            selector: CSS selector (if None, gets full page HTML)
            outer: If True, includes the element itself; if False, only inner HTML
            timeout: Action timeout in milliseconds

        Returns:
            HTML content
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
                locator = session.page.locator(selector)
                if outer:
                    return await locator.evaluate("el => el.outerHTML", timeout=action_timeout)
                else:
                    return await locator.inner_html(timeout=action_timeout)
            else:
                return await session.page.content()
        except Exception as e:
            return f"Error getting HTML: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def get_attribute(
        selector: str,
        attribute: str,
        timeout: int | None = None,
    ) -> str:
        """
        Get an attribute value from an element.

        Args:
            selector: CSS selector for the element
            attribute: Attribute name (e.g., "href", "src", "class")
            timeout: Action timeout in milliseconds

        Returns:
            Attribute value or null
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
            value = await session.page.locator(selector).get_attribute(
                attribute, timeout=action_timeout
            )
            return value if value is not None else "null"
        except Exception as e:
            return f"Error getting attribute: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def query_selector_all(
        selector: str,
        extract: str = "text",
        limit: int = 100,
        timeout: int | None = None,
    ) -> str:
        """
        Find all elements matching a selector and extract data.

        Args:
            selector: CSS selector
            extract: What to extract - "text", "html", or an attribute name
            limit: Maximum number of elements to return
            timeout: Action timeout in milliseconds

        Returns:
            JSON array of extracted values
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
            elements = await session.page.locator(selector).all()
            results = []

            for i, el in enumerate(elements[:limit]):
                if extract == "text":
                    results.append(await el.inner_text(timeout=action_timeout))
                elif extract == "html":
                    results.append(await el.inner_html(timeout=action_timeout))
                else:
                    results.append(await el.get_attribute(extract, timeout=action_timeout))

            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error querying elements: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def inspect_element(selector: str, timeout: int | None = None) -> str:
        """
        Get detailed information about an element.

        Args:
            selector: CSS selector for the element
            timeout: Action timeout in milliseconds

        Returns:
            JSON object with element details
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
            locator = session.page.locator(selector)

            info = await locator.evaluate(
                """el => ({
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className,
                    name: el.name,
                    type: el.type,
                    value: el.value,
                    href: el.href,
                    src: el.src,
                    innerText: el.innerText?.substring(0, 200),
                    innerHTML: el.innerHTML?.substring(0, 500),
                    isVisible: el.offsetParent !== null,
                    rect: el.getBoundingClientRect(),
                    attributes: Array.from(el.attributes || []).map(a => ({name: a.name, value: a.value})),
                    computedStyle: {
                        display: getComputedStyle(el).display,
                        visibility: getComputedStyle(el).visibility,
                        opacity: getComputedStyle(el).opacity,
                    }
                })""",
                timeout=action_timeout,
            )

            return json.dumps(info, indent=2)
        except Exception as e:
            return f"Error inspecting element: {str(e)}"
