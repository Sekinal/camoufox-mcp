"""
Tool registration for Camoufox MCP Server.

Registers all tools with the FastMCP server instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.camoufox_mcp.logging import get_logger

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = get_logger(__name__)


def register_all_tools(mcp: FastMCP) -> None:
    """
    Register all tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """
    # Import and register each tool module
    from src.camoufox_mcp.tools import browser
    from src.camoufox_mcp.tools import navigation
    from src.camoufox_mcp.tools import interaction
    from src.camoufox_mcp.tools import extraction
    from src.camoufox_mcp.tools import network
    from src.camoufox_mcp.tools import screenshot
    from src.camoufox_mcp.tools import javascript
    from src.camoufox_mcp.tools import waiting
    from src.camoufox_mcp.tools import storage
    from src.camoufox_mcp.tools import frames
    from src.camoufox_mcp.tools import analysis
    from src.camoufox_mcp.tools import debug
    from src.camoufox_mcp.tools import compound
    # New Playwright MCP-inspired modules
    from src.camoufox_mcp.tools import accessibility
    from src.camoufox_mcp.tools import mouse
    from src.camoufox_mcp.tools import pdf
    from src.camoufox_mcp.tools import assertions
    from src.camoufox_mcp.tools import tracing
    # Chrome DevTools MCP-inspired modules
    from src.camoufox_mcp.tools import emulation
    from src.camoufox_mcp.tools import performance

    # Register browser management tools
    browser.register(mcp)
    logger.debug("tools_registered", module="browser")

    # Register navigation tools
    navigation.register(mcp)
    logger.debug("tools_registered", module="navigation")

    # Register page interaction tools
    interaction.register(mcp)
    logger.debug("tools_registered", module="interaction")

    # Register content extraction tools
    extraction.register(mcp)
    logger.debug("tools_registered", module="extraction")

    # Register network analysis tools
    network.register(mcp)
    logger.debug("tools_registered", module="network")

    # Register screenshot tools
    screenshot.register(mcp)
    logger.debug("tools_registered", module="screenshot")

    # Register JavaScript tools
    javascript.register(mcp)
    logger.debug("tools_registered", module="javascript")

    # Register waiting tools
    waiting.register(mcp)
    logger.debug("tools_registered", module="waiting")

    # Register storage tools
    storage.register(mcp)
    logger.debug("tools_registered", module="storage")

    # Register frame/dialog tools
    frames.register(mcp)
    logger.debug("tools_registered", module="frames")

    # Register analysis tools (NEW)
    analysis.register(mcp)
    logger.debug("tools_registered", module="analysis")

    # Register debug tools
    debug.register(mcp)
    logger.debug("tools_registered", module="debug")

    # Register compound action tools (batch operations, smart selectors)
    compound.register(mcp)
    logger.debug("tools_registered", module="compound")

    # Register accessibility tools (snapshots for LLM understanding)
    accessibility.register(mcp)
    logger.debug("tools_registered", module="accessibility")

    # Register coordinate-based mouse tools (vision-based interactions)
    mouse.register(mcp)
    logger.debug("tools_registered", module="mouse")

    # Register PDF generation tools
    pdf.register(mcp)
    logger.debug("tools_registered", module="pdf")

    # Register test assertion tools (verification and validation)
    assertions.register(mcp)
    logger.debug("tools_registered", module="assertions")

    # Register tracing tools (trace recording for debugging)
    tracing.register(mcp)
    logger.debug("tools_registered", module="tracing")

    # Register device/network emulation tools
    emulation.register(mcp)
    logger.debug("tools_registered", module="emulation")

    # Register performance analysis tools
    performance.register(mcp)
    logger.debug("tools_registered", module="performance")

    logger.info("all_tools_registered", total_modules=20)
