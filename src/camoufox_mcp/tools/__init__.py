"""
Tool modules for Camoufox MCP Server.

Each module contains related tools grouped by functionality:
- browser: Browser management (launch, close, pages)
- navigation: URL navigation and history
- interaction: Page interactions (click, fill, type)
- extraction: Content extraction (text, HTML, attributes)
- network: Network analysis and capture
- screenshot: Screenshots and viewport
- javascript: JavaScript evaluation
- waiting: Wait mechanisms
- storage: Cookies and localStorage
- frames: Frame and dialog handling
- analysis: Website analysis tools (anti-bot detection, structure analysis)
"""

from src.camoufox_mcp.tools.registration import register_all_tools

__all__ = ["register_all_tools"]
