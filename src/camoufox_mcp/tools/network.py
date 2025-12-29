"""
Network analysis tools for Camoufox MCP Server.

Tools: get_network_log, clear_network_log, set_network_capture, wait_for_request, wait_for_response
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.instrumentation import instrumented_tool
from src.camoufox_mcp.session import get_session

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register network analysis tools with the MCP server."""

    @mcp.tool()
    @instrumented_tool(log_outputs=False)
    async def get_network_log(
        url_filter: str | None = None,
        method_filter: str | None = None,
        status_filter: int | None = None,
        resource_type_filter: str | None = None,
        limit: int = 50,
        include_timing: bool = False,
    ) -> str:
        """
        Get captured network requests/responses.

        Args:
            url_filter: Filter by URL substring
            method_filter: Filter by HTTP method (GET, POST, etc.)
            status_filter: Filter by status code
            resource_type_filter: Filter by resource type (document, script, xhr, fetch, etc.)
            limit: Maximum number of entries to return
            include_timing: Include timing information

        Returns:
            JSON array of network entries
        """
        session = get_session()
        config = get_config()

        entries = session.network_log.copy()

        # Apply filters
        if url_filter:
            entries = [e for e in entries if url_filter.lower() in e.url.lower()]
        if method_filter:
            entries = [e for e in entries if e.method.upper() == method_filter.upper()]
        if status_filter:
            entries = [e for e in entries if e.status == status_filter]
        if resource_type_filter:
            entries = [e for e in entries if e.resource_type == resource_type_filter]

        # Limit results
        entries = entries[-limit:]

        result = []
        for e in entries:
            entry_dict = {
                "url": e.url,
                "method": e.method,
                "status": e.status,
                "resource_type": e.resource_type,
                "request_headers": e.request_headers,
                "response_headers": e.response_headers,
            }

            # Include bodies if captured
            if e.request_body:
                max_size = config.network.max_body_size
                entry_dict["request_body"] = (
                    e.request_body[:max_size] if len(e.request_body) > max_size else e.request_body
                )
            if e.response_body:
                max_size = config.network.max_body_size
                entry_dict["response_body"] = (
                    e.response_body[:max_size]
                    if len(e.response_body) > max_size
                    else e.response_body
                )

            if include_timing and e.timing:
                entry_dict["timing"] = e.timing
                entry_dict["duration_ms"] = e.duration_ms

            result.append(entry_dict)

        return json.dumps(result, indent=2)

    @mcp.tool()
    @instrumented_tool()
    async def clear_network_log() -> str:
        """
        Clear the captured network log.

        Returns:
            Confirmation message
        """
        session = get_session()
        count = len(session.network_log)
        session.network_log.clear()
        return f"Network log cleared ({count} entries removed)."

    @mcp.tool()
    @instrumented_tool()
    async def set_network_capture(
        enabled: bool = True,
        capture_bodies: bool = False,
    ) -> str:
        """
        Configure network capture settings.

        Args:
            enabled: Enable or disable network capture
            capture_bodies: Also capture request/response bodies (can be large!)

        Returns:
            Confirmation
        """
        session = get_session()
        session.capture_network = enabled
        session.capture_bodies = capture_bodies
        return (
            f"Network capture: {'enabled' if enabled else 'disabled'}, "
            f"bodies: {'captured' if capture_bodies else 'not captured'}"
        )

    @mcp.tool()
    @instrumented_tool()
    async def wait_for_request(
        url_pattern: str,
        timeout: int | None = None,
    ) -> str:
        """
        Wait for a network request matching a URL pattern.

        Args:
            url_pattern: URL substring or pattern to match
            timeout: Maximum wait time in milliseconds

        Returns:
            Request details when matched
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        wait_timeout = timeout or config.timeouts.network_wait

        try:
            async with session.page.expect_request(
                lambda req: url_pattern in req.url, timeout=wait_timeout
            ) as request_info:
                request = await request_info.value
                return json.dumps(
                    {
                        "url": request.url,
                        "method": request.method,
                        "headers": dict(request.headers),
                        "post_data": request.post_data,
                        "resource_type": request.resource_type,
                    },
                    indent=2,
                )
        except Exception as e:
            return f"Error waiting for request: {str(e)}"

    @mcp.tool()
    @instrumented_tool()
    async def wait_for_response(
        url_pattern: str,
        timeout: int | None = None,
        include_body: bool = False,
    ) -> str:
        """
        Wait for a network response matching a URL pattern.

        Args:
            url_pattern: URL substring or pattern to match
            timeout: Maximum wait time in milliseconds
            include_body: Include response body in result

        Returns:
            Response details when matched
        """
        session = get_session()

        if not session.page:
            return "Error: No active page."

        config = get_config()
        wait_timeout = timeout or config.timeouts.network_wait

        try:
            async with session.page.expect_response(
                lambda resp: url_pattern in resp.url, timeout=wait_timeout
            ) as response_info:
                response = await response_info.value

                result = {
                    "url": response.url,
                    "status": response.status,
                    "headers": dict(response.headers),
                }

                if include_body:
                    try:
                        body = await response.text()
                        max_size = config.network.max_body_size
                        result["body"] = body[:max_size] if len(body) > max_size else body
                    except Exception:
                        result["body"] = None

                return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error waiting for response: {str(e)}"
