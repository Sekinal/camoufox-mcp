"""
Browser session management for Camoufox MCP Server.

Provides the BrowserSession class with health checks, recovery, and network capture.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from camoufox.async_api import AsyncCamoufox
from playwright.async_api import Page, Request, Response

from src.camoufox_mcp.config import get_config
from src.camoufox_mcp.logging import get_logger
from src.camoufox_mcp.metrics import get_metrics
from src.camoufox_mcp.models import BrowserInfo, NetworkEntry, PageInfo

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

logger = get_logger(__name__)


class BrowserSession:
    """
    Manages a Camoufox browser session with network capture, health checks, and recovery.

    This class handles:
    - Browser lifecycle (launch, close, crash recovery)
    - Multiple page/tab management
    - Network request/response capture
    - Health monitoring
    """

    def __init__(self) -> None:
        self.browser: AsyncCamoufox | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.pages: dict[str, Page] = {}
        self.network_log: list[NetworkEntry] = []
        self.capture_network: bool = True
        self.capture_bodies: bool = False
        self._browser_cm = None
        self._launch_time: datetime | None = None
        self._config = get_config()
        self._metrics = get_metrics()
        self._active_page_id: str | None = None

    @property
    def is_running(self) -> bool:
        """Check if browser is currently running."""
        return self.browser is not None

    @property
    def uptime_seconds(self) -> float:
        """Get browser session uptime in seconds."""
        if self._launch_time is None:
            return 0.0
        return (datetime.now(timezone.utc) - self._launch_time).total_seconds()

    async def launch(
        self,
        headless: bool | None = None,
        proxy: dict | None = None,
        os_type: str | list[str] | None = None,
        humanize: bool | float | None = None,
        geoip: bool = False,
        block_images: bool = False,
        locale: str | None = None,
    ) -> str:
        """
        Launch a new browser session.

        Args:
            headless: Run in headless mode (uses config default if None)
            proxy: Proxy configuration dict with server, username, password
            os_type: OS to spoof (windows, macos, linux, random)
            humanize: Enable human-like cursor movement
            geoip: Auto-detect location from IP
            block_images: Block image loading
            locale: Browser locale (e.g., "en-US")

        Returns:
            Status message
        """
        if self.browser is not None:
            return "Browser already running. Close it first with close_browser."

        # Apply defaults from config
        if headless is None:
            headless = self._config.browser.default_headless
        if humanize is None:
            humanize = self._config.browser.default_humanize

        kwargs = {
            "headless": headless,
            "humanize": humanize,
            "geoip": geoip,
            "block_images": block_images,
        }

        if proxy:
            kwargs["proxy"] = proxy
        if os_type:
            kwargs["os"] = os_type
        if locale:
            kwargs["locale"] = locale

        try:
            self._browser_cm = AsyncCamoufox(**kwargs)
            self.browser = await asyncio.wait_for(
                self._browser_cm.__aenter__(),
                timeout=self._config.timeouts.browser_launch / 1000,
            )

            # Initialize network capture settings from config
            self.capture_network = self._config.network.capture_by_default
            self.capture_bodies = self._config.network.capture_bodies_by_default

            # Create initial page
            self.page = await self.browser.new_page()
            self.pages["main"] = self.page
            self._active_page_id = "main"

            # Set up network capture
            await self._setup_network_capture(self.page)

            # Set default viewport
            await self.page.set_viewport_size({
                "width": self._config.browser.default_viewport_width,
                "height": self._config.browser.default_viewport_height,
            })

            self._launch_time = datetime.now(timezone.utc)
            self._metrics.record_browser_launch()
            self._metrics.record_page_created()

            logger.info(
                "browser_launched",
                headless=headless,
                humanize=humanize,
                proxy_enabled=proxy is not None,
            )

            return "Browser launched successfully. Main page created."

        except asyncio.TimeoutError:
            logger.error("browser_launch_timeout")
            await self._cleanup()
            return "Error: Browser launch timed out."
        except Exception as e:
            logger.error("browser_launch_error", error=str(e))
            await self._cleanup()
            return f"Error launching browser: {str(e)}"

    async def _setup_network_capture(self, page: Page) -> None:
        """Set up network request/response capture for a page."""

        async def on_request(request: Request) -> None:
            if not self.capture_network:
                return

            entry = NetworkEntry(
                url=request.url,
                method=request.method,
                request_headers=dict(request.headers),
                resource_type=request.resource_type,
            )

            if self.capture_bodies:
                try:
                    entry.request_body = request.post_data
                except Exception:
                    pass

            # Enforce max log size
            if len(self.network_log) >= self._config.network.max_log_size:
                self.network_log.pop(0)

            self.network_log.append(entry)

            # Record network metrics
            try:
                domain = urlparse(request.url).netloc
                self._metrics.record_network_request(domain, request.resource_type, True)
            except Exception:
                pass

        async def on_response(response: Response) -> None:
            if not self.capture_network:
                return

            # Find matching request entry
            for entry in reversed(self.network_log):
                if entry.url == response.url and entry.status is None:
                    entry.status = response.status
                    entry.response_headers = dict(response.headers)

                    if self.capture_bodies:
                        try:
                            body = await response.text()
                            max_size = self._config.network.max_body_size
                            entry.response_body = body[:max_size] if len(body) > max_size else body
                        except Exception:
                            pass

                    try:
                        timing = response.request.timing
                        entry.timing = timing if isinstance(timing, dict) else {}
                        if "responseEnd" in entry.timing and "requestStart" in entry.timing:
                            entry.duration_ms = (
                                entry.timing["responseEnd"] - entry.timing["requestStart"]
                            )
                    except Exception:
                        pass

                    break

        page.on("request", on_request)
        page.on("response", on_response)

    async def close(self) -> str:
        """Close the browser session and clean up resources."""
        await self._cleanup()
        logger.info("browser_closed")
        return "Browser closed successfully."

    async def _cleanup(self) -> None:
        """Internal cleanup method."""
        if self._browser_cm:
            try:
                await asyncio.wait_for(
                    self._browser_cm.__aexit__(None, None, None),
                    timeout=self._config.timeouts.page_close / 1000,
                )
            except Exception as e:
                logger.warning("browser_cleanup_error", error=str(e))

        self.browser = None
        self.context = None
        self.page = None
        self.pages.clear()
        self.network_log.clear()
        self._browser_cm = None
        self._launch_time = None
        self._active_page_id = None

    async def health_check(self) -> dict:
        """
        Check browser health and responsiveness.

        Returns:
            Dict with health status and diagnostics
        """
        if not self.browser:
            return {
                "healthy": False,
                "status": "stopped",
                "message": "Browser not running",
            }

        try:
            # Try a simple operation to verify browser is responsive
            if self.page:
                start = time.perf_counter()
                await asyncio.wait_for(
                    self.page.evaluate("() => 1 + 1"),
                    timeout=5.0,
                )
                latency_ms = (time.perf_counter() - start) * 1000

                return {
                    "healthy": True,
                    "status": "running",
                    "latency_ms": round(latency_ms, 2),
                    "uptime_seconds": round(self.uptime_seconds, 2),
                    "page_count": len(self.pages),
                    "network_log_size": len(self.network_log),
                }
            else:
                return {
                    "healthy": False,
                    "status": "degraded",
                    "message": "No active page",
                }

        except asyncio.TimeoutError:
            return {
                "healthy": False,
                "status": "unresponsive",
                "message": "Browser not responding (timeout)",
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "message": str(e),
            }

    async def recover(self) -> str:
        """
        Attempt to recover from a browser crash or unresponsive state.

        Returns:
            Recovery status message
        """
        if not self._config.browser.auto_recover:
            return "Auto-recovery is disabled in configuration."

        logger.info("browser_recovery_attempt")
        self._metrics.record_browser_crash()

        # Save current state
        last_url = None
        if self.page:
            try:
                last_url = self.page.url
            except Exception:
                pass

        # Force cleanup
        await self._cleanup()

        # Relaunch
        result = await self.launch()

        # Try to navigate back to last URL
        if last_url and last_url != "about:blank" and self.page:
            try:
                await self.page.goto(last_url, wait_until="domcontentloaded")
                logger.info("browser_recovered", restored_url=last_url)
                return f"Browser recovered. Restored to: {last_url}"
            except Exception as e:
                logger.warning("recovery_navigation_failed", error=str(e))
                return f"Browser recovered but couldn't restore URL: {str(e)}"

        return result

    async def new_page(self, page_id: str = "new") -> str:
        """Create a new browser page/tab."""
        if not self.browser:
            return "Error: Browser not launched. Call launch_browser first."

        if len(self.pages) >= self._config.browser.max_pages:
            return f"Error: Maximum page limit ({self._config.browser.max_pages}) reached."

        try:
            page = await self.browser.new_page()
            await self._setup_network_capture(page)
            await page.set_viewport_size({
                "width": self._config.browser.default_viewport_width,
                "height": self._config.browser.default_viewport_height,
            })

            self.pages[page_id] = page
            self.page = page
            self._active_page_id = page_id
            self._metrics.record_page_created()

            logger.info("page_created", page_id=page_id)
            return f"New page created with id '{page_id}' and set as active."

        except Exception as e:
            logger.error("page_creation_error", error=str(e))
            return f"Error creating page: {str(e)}"

    async def switch_page(self, page_id: str) -> str:
        """Switch to a different page/tab."""
        if page_id not in self.pages:
            available = list(self.pages.keys())
            return f"Error: Page '{page_id}' not found. Available: {available}"

        self.page = self.pages[page_id]
        self._active_page_id = page_id
        logger.debug("page_switched", page_id=page_id)
        return f"Switched to page '{page_id}'."

    async def close_page(self, page_id: str) -> str:
        """Close a specific page/tab."""
        if page_id not in self.pages:
            return f"Error: Page '{page_id}' not found."

        if page_id == "main" and len(self.pages) == 1:
            return "Error: Cannot close the last remaining page."

        try:
            page = self.pages[page_id]
            await page.close()
            del self.pages[page_id]
            self._metrics.record_page_closed()

            # Switch to another page if we closed the active one
            if self._active_page_id == page_id:
                self._active_page_id = next(iter(self.pages.keys()))
                self.page = self.pages[self._active_page_id]

            logger.info("page_closed", page_id=page_id)
            return f"Page '{page_id}' closed."

        except Exception as e:
            logger.error("page_close_error", page_id=page_id, error=str(e))
            return f"Error closing page: {str(e)}"

    def get_info(self) -> BrowserInfo:
        """Get information about the current browser session."""
        pages_info = []
        for page_id, page in self.pages.items():
            try:
                url = page.url
                title = None  # Would need async call
            except Exception:
                url = "unknown"
                title = None

            pages_info.append(PageInfo(
                page_id=page_id,
                url=url,
                title=title,
                is_active=page_id == self._active_page_id,
            ))

        return BrowserInfo(
            status="running" if self.browser else "stopped",
            pages=pages_info,
            active_page_id=self._active_page_id,
            network_capture_enabled=self.capture_network,
            capture_bodies=self.capture_bodies,
            network_log_size=len(self.network_log),
            uptime_seconds=self.uptime_seconds,
            total_requests=self._metrics._total_requests,
            total_errors=self._metrics._total_errors,
        )


# Global browser session instance
_session: BrowserSession | None = None


def get_session() -> BrowserSession:
    """Get the global browser session."""
    global _session
    if _session is None:
        _session = BrowserSession()
    return _session


def reset_session() -> None:
    """Reset the global session (useful for testing)."""
    global _session
    _session = None
