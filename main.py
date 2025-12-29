"""
Camoufox MCP Server - Entry Point

Production-ready browser automation and web scraping analysis tools for Claude.
This server provides comprehensive browser control, network analysis,
and page interaction capabilities using Camoufox (anti-detect Firefox).

Usage:
    python main.py                    # Run with default stdio transport
    camoufox-mcp                      # Run via installed command

Environment Variables:
    CAMOUFOX_LOG_LEVEL               # DEBUG, INFO, WARNING, ERROR (default: INFO)
    CAMOUFOX_LOG_FORMAT              # json, console (default: json)
    CAMOUFOX_HEADLESS                # true, false (default: true)
    CAMOUFOX_TIMEOUT_NAVIGATION      # Navigation timeout in ms (default: 30000)
    See config.py for full list of configuration options.
"""

from src.camoufox_mcp.server import run_server


def main() -> None:
    """Run the Camoufox MCP server."""
    run_server()


if __name__ == "__main__":
    main()
