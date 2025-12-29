"""
FastMCP server setup for Camoufox MCP Server.

Creates and configures the MCP server with all tools registered.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.camoufox_mcp.logging import ensure_logging_configured, get_logger

logger = get_logger(__name__)


def create_server() -> FastMCP:
    """
    Create and configure the Camoufox MCP server.

    Returns:
        Configured FastMCP server instance with all tools registered
    """
    # Initialize logging
    ensure_logging_configured()

    logger.info("server_init", message="Creating Camoufox MCP server")

    # Create the MCP server
    mcp = FastMCP("camoufox")

    # Register all tools
    from src.camoufox_mcp.tools.registration import register_all_tools
    register_all_tools(mcp)

    logger.info("server_ready", message="Camoufox MCP server initialized")

    return mcp


def run_server() -> None:
    """Run the Camoufox MCP server with stdio transport."""
    server = create_server()
    server.run(transport="stdio")
