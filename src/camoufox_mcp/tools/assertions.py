"""
Test assertion tools for Camoufox MCP Server.

Provides verification tools for testing and validation scenarios.

Tools: verify_element_visible, verify_text_visible, verify_value, verify_element_hidden,
       generate_locator, expect_element
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_selector

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register assertion tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool()
    async def verify_element_visible(
        selector: str,
        timeout: int | None = None,
    ) -> str:
        """
        Verify that an element is visible on the page.

        Args:
            selector: CSS selector for the element to verify
            timeout: Maximum time to wait for visibility in milliseconds

        Returns:
            Verification result (pass/fail with details)
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
            await locator.wait_for(state="visible", timeout=action_timeout)

            # Get additional info
            count = await locator.count()

            return f"PASS: Element '{selector}' is visible. Found {count} matching element(s)."
        except Exception as e:
            return f"FAIL: Element '{selector}' is not visible. Error: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def verify_element_hidden(
        selector: str,
        timeout: int | None = None,
    ) -> str:
        """
        Verify that an element is hidden or not present on the page.

        Args:
            selector: CSS selector for the element to verify
            timeout: Maximum time to wait for element to be hidden in milliseconds

        Returns:
            Verification result (pass/fail with details)
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
            await locator.wait_for(state="hidden", timeout=action_timeout)

            return f"PASS: Element '{selector}' is hidden or not present."
        except Exception as e:
            return f"FAIL: Element '{selector}' is still visible. Error: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def verify_text_visible(
        text: str,
        exact: bool = False,
        timeout: int | None = None,
    ) -> str:
        """
        Verify that specific text is visible on the page.

        Args:
            text: Text content to find
            exact: If True, match exact text. If False, match partial text.
            timeout: Maximum time to wait in milliseconds

        Returns:
            Verification result (pass/fail with details)
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            if exact:
                locator = session.page.get_by_text(text, exact=True)
            else:
                locator = session.page.get_by_text(text)

            await locator.first.wait_for(state="visible", timeout=action_timeout)

            count = await locator.count()
            return f"PASS: Text '{text}' is visible. Found {count} occurrence(s)."
        except Exception as e:
            return f"FAIL: Text '{text}' is not visible. Error: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def verify_value(
        selector: str,
        expected_value: str,
        timeout: int | None = None,
    ) -> str:
        """
        Verify the value of an input element.

        Args:
            selector: CSS selector for the input element
            expected_value: Expected value to verify
            timeout: Maximum time to wait in milliseconds

        Returns:
            Verification result (pass/fail with actual value)
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
            await locator.wait_for(state="visible", timeout=action_timeout)

            actual_value = await locator.input_value()

            if actual_value == expected_value:
                return f"PASS: Value matches. Expected '{expected_value}', got '{actual_value}'."
            else:
                return f"FAIL: Value mismatch. Expected '{expected_value}', got '{actual_value}'."
        except Exception as e:
            return f"FAIL: Could not get value from '{selector}'. Error: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def verify_list_visible(
        items: list[str],
        ordered: bool = False,
        timeout: int | None = None,
    ) -> str:
        """
        Verify that a list of items is visible on the page.

        Args:
            items: List of text items to verify
            ordered: If True, verify items appear in order
            timeout: Maximum time to wait in milliseconds

        Returns:
            Verification result (pass/fail with details)
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        action_timeout = timeout or config.timeouts.element_action

        try:
            results = []
            positions = []

            for item in items:
                try:
                    locator = session.page.get_by_text(item)
                    await locator.first.wait_for(state="visible", timeout=action_timeout)

                    # Get position for order checking
                    if ordered:
                        bbox = await locator.first.bounding_box()
                        if bbox:
                            positions.append((item, bbox["y"]))

                    results.append((item, True, None))
                except Exception as e:
                    results.append((item, False, str(e)))

            # Check results
            failed = [r for r in results if not r[1]]
            if failed:
                failed_items = ", ".join([f"'{r[0]}'" for r in failed])
                return f"FAIL: Some items not visible: {failed_items}"

            # Check order if required
            if ordered and positions:
                sorted_positions = sorted(positions, key=lambda x: x[1])
                actual_order = [p[0] for p in sorted_positions]
                if actual_order != items:
                    return f"FAIL: Items not in expected order. Expected: {items}, Got: {actual_order}"

            return f"PASS: All {len(items)} items are visible" + (" in correct order." if ordered else ".")

        except Exception as e:
            return f"FAIL: Error verifying list: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def generate_locator(
        selector: str,
    ) -> str:
        """
        Generate a robust locator string for an element.

        Analyzes the element and suggests the best locator strategy
        for use in tests.

        Args:
            selector: CSS selector to locate the element

        Returns:
            Suggested locator strings and strategies
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        valid, result = safe_validate(validate_selector, selector)
        if not valid:
            return f"Error: Invalid selector - {result}"

        try:
            import json

            element = session.page.locator(selector)
            count = await element.count()

            if count == 0:
                return f"Error: No element found matching '{selector}'."

            # Get element attributes
            attrs = await element.first.evaluate("""
                (el) => {
                    return {
                        tagName: el.tagName.toLowerCase(),
                        id: el.id,
                        className: el.className,
                        name: el.getAttribute('name'),
                        type: el.getAttribute('type'),
                        placeholder: el.getAttribute('placeholder'),
                        role: el.getAttribute('role'),
                        ariaLabel: el.getAttribute('aria-label'),
                        text: el.innerText?.substring(0, 100),
                        href: el.getAttribute('href'),
                        dataTestId: el.getAttribute('data-testid') || el.getAttribute('data-test-id'),
                    };
                }
            """)

            locators = []

            # Generate various locator strategies
            if attrs.get("dataTestId"):
                locators.append({
                    "strategy": "data-testid",
                    "locator": f'page.get_by_test_id("{attrs["dataTestId"]}")',
                    "reliability": "high",
                })

            if attrs.get("role") and attrs.get("ariaLabel"):
                locators.append({
                    "strategy": "role",
                    "locator": f'page.get_by_role("{attrs["role"]}", name="{attrs["ariaLabel"]}")',
                    "reliability": "high",
                })
            elif attrs.get("role"):
                locators.append({
                    "strategy": "role",
                    "locator": f'page.get_by_role("{attrs["role"]}")',
                    "reliability": "medium",
                })

            if attrs.get("placeholder"):
                locators.append({
                    "strategy": "placeholder",
                    "locator": f'page.get_by_placeholder("{attrs["placeholder"]}")',
                    "reliability": "high",
                })

            if attrs.get("ariaLabel"):
                locators.append({
                    "strategy": "aria-label",
                    "locator": f'page.get_by_label("{attrs["ariaLabel"]}")',
                    "reliability": "high",
                })

            if attrs.get("text") and len(attrs["text"]) < 50:
                clean_text = attrs["text"].strip().replace('"', '\\"')
                locators.append({
                    "strategy": "text",
                    "locator": f'page.get_by_text("{clean_text}")',
                    "reliability": "medium",
                })

            if attrs.get("id"):
                locators.append({
                    "strategy": "id",
                    "locator": f'page.locator("#{attrs["id"]}")',
                    "reliability": "high" if not any(c.isdigit() for c in attrs["id"]) else "low",
                })

            result = {
                "element": attrs,
                "count": count,
                "locators": locators,
                "original_selector": selector,
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error generating locator: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def expect_element(
        selector: str,
        assertion: str,
        expected: str | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Run an assertion on an element (Playwright expect-style).

        Args:
            selector: CSS selector for the element
            assertion: Type of assertion to run:
                      - "visible", "hidden", "enabled", "disabled"
                      - "checked", "unchecked", "focused", "editable"
                      - "empty", "attached", "detached"
                      - "has_text", "has_value", "has_attribute", "has_class"
            expected: Expected value for assertions that require one
            timeout: Maximum time to wait in milliseconds

        Returns:
            Assertion result (pass/fail with details)
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

            # State assertions
            if assertion == "visible":
                await locator.wait_for(state="visible", timeout=action_timeout)
                return f"PASS: Element '{selector}' is visible."

            elif assertion == "hidden":
                await locator.wait_for(state="hidden", timeout=action_timeout)
                return f"PASS: Element '{selector}' is hidden."

            elif assertion == "attached":
                await locator.wait_for(state="attached", timeout=action_timeout)
                return f"PASS: Element '{selector}' is attached to DOM."

            elif assertion == "detached":
                await locator.wait_for(state="detached", timeout=action_timeout)
                return f"PASS: Element '{selector}' is detached from DOM."

            elif assertion == "enabled":
                is_enabled = await locator.is_enabled()
                if is_enabled:
                    return f"PASS: Element '{selector}' is enabled."
                return f"FAIL: Element '{selector}' is not enabled."

            elif assertion == "disabled":
                is_disabled = await locator.is_disabled()
                if is_disabled:
                    return f"PASS: Element '{selector}' is disabled."
                return f"FAIL: Element '{selector}' is not disabled."

            elif assertion == "checked":
                is_checked = await locator.is_checked()
                if is_checked:
                    return f"PASS: Element '{selector}' is checked."
                return f"FAIL: Element '{selector}' is not checked."

            elif assertion == "unchecked":
                is_checked = await locator.is_checked()
                if not is_checked:
                    return f"PASS: Element '{selector}' is unchecked."
                return f"FAIL: Element '{selector}' is checked."

            elif assertion == "focused":
                is_focused = await locator.evaluate("el => document.activeElement === el")
                if is_focused:
                    return f"PASS: Element '{selector}' is focused."
                return f"FAIL: Element '{selector}' is not focused."

            elif assertion == "editable":
                is_editable = await locator.is_editable()
                if is_editable:
                    return f"PASS: Element '{selector}' is editable."
                return f"FAIL: Element '{selector}' is not editable."

            elif assertion == "empty":
                text = await locator.inner_text()
                if not text.strip():
                    return f"PASS: Element '{selector}' is empty."
                return f"FAIL: Element '{selector}' is not empty. Contains: '{text[:50]}...'"

            # Value assertions
            elif assertion == "has_text":
                if expected is None:
                    return "Error: 'expected' parameter required for 'has_text' assertion."
                text = await locator.inner_text()
                if expected in text:
                    return f"PASS: Element contains text '{expected}'."
                return f"FAIL: Element does not contain text '{expected}'. Actual: '{text[:100]}...'"

            elif assertion == "has_value":
                if expected is None:
                    return "Error: 'expected' parameter required for 'has_value' assertion."
                value = await locator.input_value()
                if value == expected:
                    return f"PASS: Element has value '{expected}'."
                return f"FAIL: Element value mismatch. Expected: '{expected}', Actual: '{value}'."

            elif assertion == "has_class":
                if expected is None:
                    return "Error: 'expected' parameter required for 'has_class' assertion."
                class_attr = await locator.get_attribute("class") or ""
                if expected in class_attr.split():
                    return f"PASS: Element has class '{expected}'."
                return f"FAIL: Element does not have class '{expected}'. Classes: '{class_attr}'."

            else:
                return f"Error: Unknown assertion type '{assertion}'."

        except Exception as e:
            return f"FAIL: Assertion '{assertion}' failed for '{selector}'. Error: {str(e)}"
