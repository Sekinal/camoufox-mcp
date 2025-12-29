"""
Tests for configuration management.
"""

import os
from unittest import mock

import pytest

from src.camoufox_mcp.config import ServerConfig, get_config, reset_config


class TestServerConfig:
    """Tests for ServerConfig."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def test_default_values(self):
        """Test default configuration values."""
        config = ServerConfig()

        assert config.timeouts.navigation == 30000
        assert config.timeouts.selector_wait == 30000
        assert config.network.capture_by_default is True
        assert config.logging.level == "INFO"
        assert config.browser.default_headless is True

    def test_from_env_defaults(self):
        """Test loading from environment with defaults."""
        reset_config()
        config = ServerConfig.from_env()

        assert config.timeouts.navigation == 30000
        assert config.browser.default_humanize is True

    def test_from_env_custom_values(self):
        """Test loading custom values from environment."""
        with mock.patch.dict(os.environ, {
            "CAMOUFOX_TIMEOUT_NAVIGATION": "60000",
            "CAMOUFOX_LOG_LEVEL": "DEBUG",
            "CAMOUFOX_HEADLESS": "false",
        }):
            reset_config()
            config = ServerConfig.from_env()

            assert config.timeouts.navigation == 60000
            assert config.logging.level == "DEBUG"
            assert config.browser.default_headless is False

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        reset_config()
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config(self):
        """Test resetting configuration."""
        config1 = get_config()
        reset_config()
        config2 = get_config()

        # Should be different instances after reset
        assert config1 is not config2


class TestTimeoutConfig:
    """Tests for timeout configuration."""

    def test_all_timeout_values(self):
        """Test all timeout values are set correctly."""
        config = ServerConfig()

        assert config.timeouts.navigation == 30000
        assert config.timeouts.selector_wait == 30000
        assert config.timeouts.network_wait == 30000
        assert config.timeouts.element_action == 5000
        assert config.timeouts.screenshot == 10000
        assert config.timeouts.js_evaluation == 5000
        assert config.timeouts.browser_launch == 60000
        assert config.timeouts.page_close == 5000


class TestNetworkConfig:
    """Tests for network configuration."""

    def test_network_defaults(self):
        """Test network configuration defaults."""
        config = ServerConfig()

        assert config.network.capture_by_default is True
        assert config.network.capture_bodies_by_default is False
        assert config.network.max_log_size == 1000
        assert config.network.max_body_size == 10000


class TestBrowserConfig:
    """Tests for browser configuration."""

    def test_browser_defaults(self):
        """Test browser configuration defaults."""
        config = ServerConfig()

        assert config.browser.default_headless is True
        assert config.browser.default_humanize is True
        assert config.browser.default_viewport_width == 1920
        assert config.browser.default_viewport_height == 1080
        assert config.browser.auto_recover is True
        assert config.browser.max_pages == 10
