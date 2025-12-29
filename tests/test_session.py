"""
Comprehensive tests for BrowserSession.

Tests session lifecycle, health checks, recovery, network capture, and page management.
Uses mocks to avoid launching actual browser.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.camoufox_mcp.session import BrowserSession, get_session, reset_session


class TestBrowserSessionInit:
    """Tests for BrowserSession initialization."""

    def test_initial_state(self):
        """Session starts in stopped state."""
        session = BrowserSession()
        assert session.browser is None
        assert session.context is None
        assert session.page is None
        assert session.pages == {}
        assert session.network_log == []
        assert session.capture_network is True
        assert session.capture_bodies is False
        assert session.is_running is False

    def test_uptime_zero_when_not_running(self):
        """Uptime is zero when browser not running."""
        session = BrowserSession()
        assert session.uptime_seconds == 0.0


class TestBrowserSessionLaunch:
    """Tests for browser launch."""

    @pytest.fixture
    def mock_camoufox(self):
        """Create mock Camoufox browser."""
        with patch("src.camoufox_mcp.session.AsyncCamoufox") as mock:
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.url = "about:blank"
            mock_page.set_viewport_size = AsyncMock()
            mock_page.on = MagicMock()
            mock_browser.new_page = AsyncMock(return_value=mock_page)

            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock.return_value = mock_cm

            yield mock, mock_browser, mock_page

    @pytest.mark.asyncio
    async def test_launch_success(self, mock_camoufox):
        """Browser launches successfully."""
        mock, mock_browser, mock_page = mock_camoufox
        session = BrowserSession()

        result = await session.launch()

        assert "successfully" in result.lower()
        assert session.is_running is True
        assert session.browser is not None
        assert session.page is not None
        assert "main" in session.pages

    @pytest.mark.asyncio
    async def test_launch_already_running(self, mock_camoufox):
        """Cannot launch when already running."""
        mock, mock_browser, mock_page = mock_camoufox
        session = BrowserSession()
        await session.launch()

        result = await session.launch()

        assert "already running" in result.lower()

    @pytest.mark.asyncio
    async def test_launch_with_proxy(self, mock_camoufox):
        """Launch with proxy configuration."""
        mock, mock_browser, mock_page = mock_camoufox
        session = BrowserSession()

        proxy = {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        result = await session.launch(proxy=proxy)

        assert "successfully" in result.lower()
        # Verify proxy was passed
        mock.assert_called_once()
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("proxy") == proxy

    @pytest.mark.asyncio
    async def test_launch_headless(self, mock_camoufox):
        """Launch in headless mode."""
        mock, mock_browser, mock_page = mock_camoufox
        session = BrowserSession()

        await session.launch(headless=True)

        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("headless") is True

    @pytest.mark.asyncio
    async def test_launch_with_os_type(self, mock_camoufox):
        """Launch with OS spoofing."""
        mock, mock_browser, mock_page = mock_camoufox
        session = BrowserSession()

        await session.launch(os_type="windows")

        call_kwargs = mock.call_args.kwargs
        assert call_kwargs.get("os") == "windows"

    @pytest.mark.asyncio
    async def test_launch_timeout(self, mock_camoufox):
        """Handle launch timeout."""
        mock, mock_browser, mock_page = mock_camoufox

        async def slow_enter():
            await asyncio.sleep(100)
            return mock_browser

        mock.return_value.__aenter__ = slow_enter

        session = BrowserSession()
        # Patch config to have short timeout
        session._config.timeouts.browser_launch = 100  # 100ms

        result = await session.launch()

        assert "timed out" in result.lower() or "timeout" in result.lower()

    @pytest.mark.asyncio
    async def test_launch_error(self, mock_camoufox):
        """Handle launch error."""
        mock, mock_browser, mock_page = mock_camoufox
        mock.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("Launch failed"))

        session = BrowserSession()
        result = await session.launch()

        assert "error" in result.lower()
        assert session.is_running is False


class TestBrowserSessionClose:
    """Tests for browser close."""

    @pytest.fixture
    def running_session(self):
        """Create a session with mocked running browser."""
        session = BrowserSession()
        session.browser = AsyncMock()
        session.context = AsyncMock()
        session.page = AsyncMock()
        session.pages = {"main": session.page}
        session._browser_cm = AsyncMock()
        session._browser_cm.__aexit__ = AsyncMock()
        session._launch_time = datetime.now(timezone.utc)
        return session

    @pytest.mark.asyncio
    async def test_close_success(self, running_session):
        """Browser closes successfully."""
        result = await running_session.close()

        assert "successfully" in result.lower()
        assert running_session.browser is None
        assert running_session.page is None
        assert running_session.pages == {}

    @pytest.mark.asyncio
    async def test_close_clears_network_log(self, running_session):
        """Close clears network log."""
        running_session.network_log = [MagicMock(), MagicMock()]

        await running_session.close()

        assert running_session.network_log == []

    @pytest.mark.asyncio
    async def test_close_when_not_running(self):
        """Close when not running is safe."""
        session = BrowserSession()
        result = await session.close()

        assert "successfully" in result.lower()


class TestBrowserSessionHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_not_running(self):
        """Health check when browser not running."""
        session = BrowserSession()

        result = await session.health_check()

        assert result["healthy"] is False
        assert result["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Health check when browser is healthy."""
        session = BrowserSession()
        session.browser = AsyncMock()
        session.page = AsyncMock()
        session.page.evaluate = AsyncMock(return_value=2)
        session._launch_time = datetime.now(timezone.utc)
        session.pages = {"main": session.page}
        session.network_log = []

        result = await session.health_check()

        assert result["healthy"] is True
        assert result["status"] == "running"
        assert "latency_ms" in result
        assert result["page_count"] == 1

    @pytest.mark.asyncio
    async def test_health_check_no_page(self):
        """Health check when no active page."""
        session = BrowserSession()
        session.browser = AsyncMock()
        session.page = None

        result = await session.health_check()

        assert result["healthy"] is False
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Health check times out."""
        session = BrowserSession()
        session.browser = AsyncMock()
        session.page = AsyncMock()

        async def slow_evaluate(script):
            await asyncio.sleep(10)
            return 2

        session.page.evaluate = slow_evaluate

        result = await session.health_check()

        assert result["healthy"] is False
        assert result["status"] == "unresponsive"

    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """Health check handles errors."""
        session = BrowserSession()
        session.browser = AsyncMock()
        session.page = AsyncMock()
        session.page.evaluate = AsyncMock(side_effect=RuntimeError("Page crashed"))

        result = await session.health_check()

        assert result["healthy"] is False
        assert result["status"] == "error"


class TestBrowserSessionRecovery:
    """Tests for browser recovery."""

    @pytest.fixture
    def mock_camoufox_for_recovery(self):
        """Create mock for recovery tests."""
        with patch("src.camoufox_mcp.session.AsyncCamoufox") as mock:
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.url = "about:blank"
            mock_page.set_viewport_size = AsyncMock()
            mock_page.on = MagicMock()
            mock_page.goto = AsyncMock()
            mock_browser.new_page = AsyncMock(return_value=mock_page)

            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock.return_value = mock_cm

            yield mock, mock_browser, mock_page

    @pytest.mark.asyncio
    async def test_recover_restores_browser(self, mock_camoufox_for_recovery):
        """Recovery restores browser."""
        mock, mock_browser, mock_page = mock_camoufox_for_recovery
        session = BrowserSession()
        session.browser = AsyncMock()  # "Crashed" browser
        session.page = AsyncMock()
        session.page.url = "https://example.com"
        session._browser_cm = AsyncMock()
        session._browser_cm.__aexit__ = AsyncMock()

        result = await session.recover()

        assert session.is_running is True

    @pytest.mark.asyncio
    async def test_recover_disabled(self):
        """Recovery when disabled in config."""
        session = BrowserSession()
        session._config.browser.auto_recover = False

        result = await session.recover()

        assert "disabled" in result.lower()


class TestBrowserSessionPages:
    """Tests for page/tab management."""

    @pytest.fixture
    def session_with_browser(self):
        """Create session with mocked browser."""
        session = BrowserSession()
        session.browser = AsyncMock()

        mock_page = AsyncMock()
        mock_page.url = "about:blank"
        mock_page.set_viewport_size = AsyncMock()
        mock_page.on = MagicMock()
        mock_page.close = AsyncMock()
        session.browser.new_page = AsyncMock(return_value=mock_page)

        session.page = mock_page
        session.pages = {"main": mock_page}
        session._active_page_id = "main"
        return session

    @pytest.mark.asyncio
    async def test_new_page_success(self, session_with_browser):
        """Create new page successfully."""
        result = await session_with_browser.new_page("tab-1")

        assert "created" in result.lower()
        assert "tab-1" in session_with_browser.pages
        assert session_with_browser._active_page_id == "tab-1"

    @pytest.mark.asyncio
    async def test_new_page_limit(self, session_with_browser):
        """Cannot exceed max page limit."""
        session_with_browser._config.browser.max_pages = 2

        await session_with_browser.new_page("tab-1")
        result = await session_with_browser.new_page("tab-2")

        assert "limit" in result.lower() or "maximum" in result.lower()

    @pytest.mark.asyncio
    async def test_new_page_no_browser(self):
        """Cannot create page without browser."""
        session = BrowserSession()

        result = await session.new_page("tab-1")

        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_switch_page_success(self, session_with_browser):
        """Switch to existing page."""
        await session_with_browser.new_page("tab-1")

        result = await session_with_browser.switch_page("main")

        assert "switched" in result.lower()
        assert session_with_browser._active_page_id == "main"

    @pytest.mark.asyncio
    async def test_switch_page_not_found(self, session_with_browser):
        """Cannot switch to non-existent page."""
        result = await session_with_browser.switch_page("nonexistent")

        assert "error" in result.lower() or "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_close_page_success(self, session_with_browser):
        """Close page successfully."""
        await session_with_browser.new_page("tab-1")

        result = await session_with_browser.close_page("tab-1")

        assert "closed" in result.lower()
        assert "tab-1" not in session_with_browser.pages

    @pytest.mark.asyncio
    async def test_close_last_page(self, session_with_browser):
        """Cannot close the last remaining page."""
        result = await session_with_browser.close_page("main")

        assert "error" in result.lower() or "cannot close" in result.lower()

    @pytest.mark.asyncio
    async def test_close_page_switches_active(self, session_with_browser):
        """Closing active page switches to another."""
        await session_with_browser.new_page("tab-1")
        session_with_browser._active_page_id = "tab-1"

        await session_with_browser.close_page("tab-1")

        assert session_with_browser._active_page_id == "main"


class TestBrowserSessionInfo:
    """Tests for get_info method."""

    def test_info_stopped(self):
        """Info when browser stopped."""
        session = BrowserSession()

        info = session.get_info()

        assert info.status == "stopped"
        assert info.pages == []
        assert info.active_page_id is None

    def test_info_running(self):
        """Info when browser running."""
        session = BrowserSession()
        session.browser = AsyncMock()

        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        session.page = mock_page
        session.pages = {"main": mock_page}
        session._active_page_id = "main"
        session.capture_network = True
        session.capture_bodies = True
        session.network_log = [MagicMock()]
        session._launch_time = datetime.now(timezone.utc)

        info = session.get_info()

        assert info.status == "running"
        assert len(info.pages) == 1
        assert info.pages[0].page_id == "main"
        assert info.pages[0].is_active is True
        assert info.network_capture_enabled is True
        assert info.network_log_size == 1


class TestGlobalSession:
    """Tests for global session management."""

    def test_get_session_creates(self):
        """get_session creates session if none exists."""
        reset_session()

        session = get_session()

        assert session is not None
        assert isinstance(session, BrowserSession)

    def test_get_session_singleton(self):
        """get_session returns same instance."""
        reset_session()

        session1 = get_session()
        session2 = get_session()

        assert session1 is session2

    def test_reset_session(self):
        """reset_session clears global session."""
        reset_session()
        session1 = get_session()

        reset_session()
        session2 = get_session()

        assert session1 is not session2


class TestNetworkCapture:
    """Tests for network capture functionality."""

    def test_capture_enabled_by_default(self):
        """Network capture is enabled by default."""
        session = BrowserSession()
        assert session.capture_network is True

    def test_capture_bodies_disabled_by_default(self):
        """Body capture is disabled by default."""
        session = BrowserSession()
        assert session.capture_bodies is False

    def test_network_log_empty_initially(self):
        """Network log starts empty."""
        session = BrowserSession()
        assert session.network_log == []
