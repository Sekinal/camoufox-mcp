"""
Cookie and storage tools for Camoufox MCP Server.

Tools: get_cookies, set_cookie, clear_cookies, get_local_storage, set_local_storage
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session
from src.camoufox_mcp.validation import safe_validate, validate_url

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register cookie and storage tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(log_outputs=False)  # Cookies can contain sensitive data
    async def get_cookies(url: str | None = None) -> str:
        """
        Get cookies from the browser context.

        Args:
            url: Optional URL to filter cookies for

        Returns:
            JSON array of cookies
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if url:
            valid, result = safe_validate(validate_url, url)
            if not valid:
                return f"Error: Invalid URL - {result}"

        try:
            context = session.page.context
            if url:
                cookies = await context.cookies(url)
            else:
                cookies = await context.cookies()
            return json.dumps(cookies, indent=2)
        except Exception as e:
            return f"Error getting cookies: {str(e)}"

    @mcp.tool()
    @instrumented_tool(sensitive_params={"value"})
    async def set_cookie(
        name: str,
        value: str,
        url: str | None = None,
        domain: str | None = None,
        path: str = "/",
        expires: int | None = None,
        http_only: bool = False,
        secure: bool = False,
        same_site: str | None = None,
    ) -> str:
        """
        Set a cookie in the browser context.

        Args:
            name: Cookie name
            value: Cookie value
            url: URL to associate with the cookie
            domain: Cookie domain
            path: Cookie path
            expires: Expiration timestamp (Unix epoch)
            http_only: HTTP-only flag
            secure: Secure flag
            same_site: SameSite attribute ("Strict", "Lax", "None")

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        if not url and not domain:
            return "Error: Either url or domain must be specified."

        if url:
            valid, result = safe_validate(validate_url, url)
            if not valid:
                return f"Error: Invalid URL - {result}"

        cookie = {
            "name": name,
            "value": value,
            "path": path,
            "httpOnly": http_only,
            "secure": secure,
        }

        if url:
            cookie["url"] = url
        if domain:
            cookie["domain"] = domain
        if expires:
            cookie["expires"] = expires
        if same_site:
            cookie["sameSite"] = same_site

        try:
            await session.page.context.add_cookies([cookie])
            return f"Cookie '{name}' set."
        except Exception as e:
            return f"Error setting cookie: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def clear_cookies() -> str:
        """
        Clear all cookies from the browser context.

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.context.clear_cookies()
            return "All cookies cleared."
        except Exception as e:
            return f"Error clearing cookies: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)  # Storage can contain sensitive data
    async def get_local_storage() -> str:
        """
        Get all localStorage data from the current page.

        Returns:
            JSON object with localStorage data
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            data = await session.page.evaluate("() => Object.entries(localStorage)")
            return json.dumps(dict(data), indent=2)
        except Exception as e:
            return f"Error getting localStorage: {str(e)}"

    @mcp.tool()
    @instrumented_tool(sensitive_params={"value"})
    async def set_local_storage(key: str, value: str) -> str:
        """
        Set a localStorage item.

        Args:
            key: Storage key
            value: Storage value

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.evaluate(
                f"localStorage.setItem({json.dumps(key)}, {json.dumps(value)})"
            )
            return f"localStorage['{key}'] set."
        except Exception as e:
            return f"Error setting localStorage: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def clear_local_storage() -> str:
        """
        Clear all localStorage data.

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.evaluate("localStorage.clear()")
            return "localStorage cleared."
        except Exception as e:
            return f"Error clearing localStorage: {str(e)}"

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_session_storage() -> str:
        """
        Get all sessionStorage data from the current page.

        Returns:
            JSON object with sessionStorage data
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            data = await session.page.evaluate("() => Object.entries(sessionStorage)")
            return json.dumps(dict(data), indent=2)
        except Exception as e:
            return f"Error getting sessionStorage: {str(e)}"

    @mcp.tool()
    @instrumented_tool(sensitive_params={"value"})
    async def set_session_storage(key: str, value: str) -> str:
        """
        Set a sessionStorage item.

        Args:
            key: Storage key
            value: Storage value

        Returns:
            Confirmation
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        try:
            await session.page.evaluate(
                f"sessionStorage.setItem({json.dumps(key)}, {json.dumps(value)})"
            )
            return f"sessionStorage['{key}'] set."
        except Exception as e:
            return f"Error setting sessionStorage: {str(e)}"
