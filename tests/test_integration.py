"""
Integration tests with mocked browser.

Tests tool functionality end-to-end with browser mocking.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.camoufox_mcp.models import NetworkEntry
from src.camoufox_mcp.session import BrowserSession, get_session, reset_session


class TestBrowserToolsIntegration:
    """Integration tests for browser management tools."""

    @pytest.fixture(autouse=True)
    def reset_session_fixture(self):
        """Reset session before and after each test."""
        reset_session()
        yield
        reset_session()

    @pytest.fixture
    def mock_camoufox(self):
        """Create comprehensive mock for Camoufox."""
        with patch("src.camoufox_mcp.session.AsyncCamoufox") as mock:
            mock_browser = AsyncMock()
            mock_page = AsyncMock()

            # Configure page mock
            mock_page.url = "about:blank"
            mock_page.title = AsyncMock(return_value="Test Page")
            mock_page.content = AsyncMock(return_value="<html><body>Test</body></html>")
            mock_page.set_viewport_size = AsyncMock()
            mock_page.on = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.reload = AsyncMock()
            mock_page.go_back = AsyncMock()
            mock_page.go_forward = AsyncMock()
            mock_page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
            mock_page.evaluate = AsyncMock(return_value={"result": "test"})
            mock_page.query_selector = AsyncMock()
            mock_page.query_selector_all = AsyncMock(return_value=[])
            mock_page.wait_for_selector = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.close = AsyncMock()

            # Configure context mock
            mock_context = AsyncMock()
            mock_context.cookies = AsyncMock(return_value=[])
            mock_context.add_cookies = AsyncMock()
            mock_context.clear_cookies = AsyncMock()
            mock_context.add_init_script = AsyncMock()
            mock_page.context = mock_context

            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.contexts = [mock_context]

            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock.return_value = mock_cm

            yield {
                "mock": mock,
                "browser": mock_browser,
                "page": mock_page,
                "context": mock_context,
            }

    @pytest.mark.asyncio
    async def test_launch_and_close_flow(self, mock_camoufox):
        """Test full launch and close workflow."""
        session = get_session()

        # Launch
        result = await session.launch()
        assert "successfully" in result.lower()
        assert session.is_running

        # Close
        result = await session.close()
        assert "successfully" in result.lower()
        assert not session.is_running

    @pytest.mark.asyncio
    async def test_page_management_flow(self, mock_camoufox):
        """Test page creation, switching, and closing."""
        session = get_session()
        await session.launch()

        # Create new page
        result = await session.new_page("tab-1")
        assert "created" in result.lower()
        assert len(session.pages) == 2

        # Switch pages
        result = await session.switch_page("main")
        assert "switched" in result.lower()
        assert session._active_page_id == "main"

        # Close page
        result = await session.close_page("tab-1")
        assert "closed" in result.lower()
        assert len(session.pages) == 1

        await session.close()

    @pytest.mark.asyncio
    async def test_health_check_flow(self, mock_camoufox):
        """Test health check on running browser."""
        session = get_session()
        await session.launch()

        result = await session.health_check()

        assert result["healthy"] is True
        assert result["status"] == "running"
        assert "latency_ms" in result

        await session.close()

    @pytest.mark.asyncio
    async def test_browser_info_flow(self, mock_camoufox):
        """Test getting browser info."""
        session = get_session()
        await session.launch()

        info = session.get_info()

        assert info.status == "running"
        assert len(info.pages) == 1
        assert info.active_page_id == "main"
        assert info.network_capture_enabled is True

        await session.close()


class TestNetworkCaptureIntegration:
    """Integration tests for network capture."""

    @pytest.fixture(autouse=True)
    def reset_session_fixture(self):
        reset_session()
        yield
        reset_session()

    def test_network_entry_creation(self):
        """Test creating network entries."""
        entry = NetworkEntry(
            url="https://api.example.com/data",
            method="POST",
            status=200,
            request_headers={"Content-Type": "application/json"},
            response_headers={"X-Request-Id": "abc123"},
            request_body='{"key": "value"}',
            response_body='{"result": "success"}',
            resource_type="xhr",
            duration_ms=150.5,
        )

        result = entry.to_dict()

        assert result["url"] == "https://api.example.com/data"
        assert result["method"] == "POST"
        assert result["status"] == 200
        assert result["duration_ms"] == 150.5

    def test_network_log_management(self):
        """Test network log accumulation."""
        session = BrowserSession()

        # Add entries
        for i in range(5):
            entry = NetworkEntry(
                url=f"https://example.com/resource/{i}",
                method="GET",
            )
            session.network_log.append(entry)

        assert len(session.network_log) == 5

        # Clear
        session.network_log.clear()
        assert len(session.network_log) == 0


class TestAnalysisToolsIntegration:
    """Integration tests for analysis tools."""

    @pytest.fixture(autouse=True)
    def reset_session_fixture(self):
        reset_session()
        yield
        reset_session()

    def test_snapshot_state_structure(self):
        """Test snapshot state data structure."""
        session = BrowserSession()
        session._snapshots = {}

        snapshot_id = "test_snapshot"
        session._snapshots[snapshot_id] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cookies": {"session": "abc123"},
            "localStorage": {"key": "value"},
            "sessionStorage": {},
            "dom": {
                "url": "https://example.com",
                "title": "Example",
                "elementCount": 500,
                "bodyHash": 12345,
            },
            "networkLogCount": 10,
        }

        assert snapshot_id in session._snapshots
        assert session._snapshots[snapshot_id]["cookies"]["session"] == "abc123"

    def test_init_scripts_tracking(self):
        """Test init script tracking."""
        session = BrowserSession()
        session._init_scripts = []

        script1 = {
            "name": "override_webdriver",
            "length": 50,
            "preview": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
        }
        script2 = {
            "name": "hook_canvas",
            "length": 200,
            "preview": "HTMLCanvasElement.prototype.toDataURL = function()...",
        }

        session._init_scripts.append(script1)
        session._init_scripts.append(script2)

        assert len(session._init_scripts) == 2
        assert session._init_scripts[0]["name"] == "override_webdriver"


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    @pytest.fixture(autouse=True)
    def reset_session_fixture(self):
        reset_session()
        yield
        reset_session()

    @pytest.mark.asyncio
    async def test_operation_without_browser(self):
        """Operations without browser return appropriate errors."""
        session = get_session()

        # Try to create page without browser
        result = await session.new_page("tab-1")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_switch_to_nonexistent_page(self):
        """Switching to non-existent page returns error."""
        session = get_session()
        session.browser = AsyncMock()
        session.pages = {"main": AsyncMock()}

        result = await session.switch_page("nonexistent")
        assert "error" in result.lower() or "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_close_nonexistent_page(self):
        """Closing non-existent page returns error."""
        session = get_session()
        session.browser = AsyncMock()
        session.pages = {"main": AsyncMock()}

        result = await session.close_page("nonexistent")
        assert "error" in result.lower() or "not found" in result.lower()


class TestConfigurationIntegration:
    """Integration tests for configuration."""

    @pytest.fixture(autouse=True)
    def reset_session_fixture(self):
        reset_session()
        yield
        reset_session()

    def test_session_uses_config(self):
        """Session uses configuration values."""
        session = BrowserSession()

        # Session should have config loaded
        assert session._config is not None
        assert session._config.browser is not None
        assert session._config.timeouts is not None
        assert session._config.network is not None

    def test_config_defaults_applied(self):
        """Default configuration values are applied."""
        session = BrowserSession()

        # Check some defaults
        assert session._config.browser.default_viewport_width > 0
        assert session._config.browser.default_viewport_height > 0
        assert session._config.timeouts.navigation > 0


class TestMetricsIntegration:
    """Integration tests for metrics collection."""

    @pytest.fixture(autouse=True)
    def reset_metrics_fixture(self):
        from src.camoufox_mcp.metrics import reset_metrics

        reset_metrics()
        yield
        reset_metrics()

    def test_session_has_metrics(self):
        """Session has metrics collector."""
        session = BrowserSession()
        assert session._metrics is not None

    def test_metrics_recorded_on_operations(self):
        """Metrics are recorded during operations."""
        from src.camoufox_mcp.metrics import get_metrics

        metrics = get_metrics()

        # Record some metrics
        metrics.record_browser_launch()
        metrics.record_page_created()
        metrics.record_page_created()
        metrics.record_page_closed()

        summary = metrics.get_summary()
        assert summary["browser"]["launches"] == 1
        assert summary["browser"]["pages_created"] == 2
        assert summary["browser"]["pages_closed"] == 1


class TestConcurrencyIntegration:
    """Integration tests for concurrent operations."""

    @pytest.fixture(autouse=True)
    def reset_session_fixture(self):
        reset_session()
        yield
        reset_session()

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Concurrent health checks don't interfere."""
        import asyncio

        session = BrowserSession()
        session.browser = AsyncMock()
        session.page = AsyncMock()
        session.page.evaluate = AsyncMock(return_value=2)
        session._launch_time = datetime.now(timezone.utc)
        session.pages = {"main": session.page}

        # Run multiple health checks concurrently
        results = await asyncio.gather(
            session.health_check(),
            session.health_check(),
            session.health_check(),
        )

        assert all(r["healthy"] for r in results)


class TestEdgeCasesIntegration:
    """Edge case integration tests."""

    @pytest.fixture(autouse=True)
    def reset_session_fixture(self):
        reset_session()
        yield
        reset_session()

    def test_empty_network_log_serialization(self):
        """Empty network log serializes correctly."""
        session = BrowserSession()
        assert session.network_log == []
        assert len(session.network_log) == 0

    def test_multiple_resets(self):
        """Multiple session resets are safe."""
        reset_session()
        reset_session()
        reset_session()

        session = get_session()
        assert session is not None

    def test_info_with_failed_page_url(self):
        """get_info handles failed page URL access."""
        session = BrowserSession()
        session.browser = AsyncMock()

        mock_page = MagicMock()
        # Simulate error when accessing URL
        type(mock_page).url = property(lambda self: (_ for _ in ()).throw(RuntimeError("Page closed")))
        session.pages = {"main": mock_page}
        session._active_page_id = "main"

        # Should not raise, should return "unknown"
        info = session.get_info()
        assert info.pages[0].url == "unknown"
