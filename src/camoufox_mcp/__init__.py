"""
Camoufox MCP Server - Production-ready browser automation for web scraping analysis.

This package provides comprehensive browser control, network analysis,
and page interaction capabilities using Camoufox (anti-detect Firefox).
"""

__version__ = "0.2.0"
__all__ = [
    "create_server",
    "BrowserSession",
    "get_logger",
    "ServerConfig",
]

from src.camoufox_mcp.server import create_server
from src.camoufox_mcp.session import BrowserSession
from src.camoufox_mcp.logging import get_logger
from src.camoufox_mcp.config import ServerConfig
