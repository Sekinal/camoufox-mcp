"""
Configuration management for Camoufox MCP Server.

Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TimeoutConfig:
    """Timeout settings in milliseconds."""

    navigation: int = 30000
    selector_wait: int = 30000
    network_wait: int = 30000
    element_action: int = 5000
    screenshot: int = 10000
    js_evaluation: int = 5000
    browser_launch: int = 60000
    page_close: int = 5000


@dataclass
class NetworkConfig:
    """Network capture settings."""

    capture_by_default: bool = True
    capture_bodies_by_default: bool = False
    max_log_size: int = 1000
    max_body_size: int = 10000  # Truncate bodies larger than this


@dataclass
class LogConfig:
    """Logging settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: Literal["json", "console"] = "json"
    include_timestamps: bool = True
    include_caller: bool = False  # Include caller file/line in logs


@dataclass
class ScreenshotConfig:
    """Screenshot settings."""

    default_dir: str = "/tmp/camoufox_screenshots"
    auto_save: bool = True  # Always save to file instead of returning base64


@dataclass
class BrowserConfig:
    """Browser launch defaults."""

    default_headless: bool = True
    default_humanize: bool = True
    default_viewport_width: int = 1920
    default_viewport_height: int = 1080
    auto_recover: bool = True  # Attempt browser restart on crash
    max_pages: int = 10


@dataclass
class ServerConfig:
    """Complete server configuration."""

    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    logging: LogConfig = field(default_factory=LogConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    screenshot: ScreenshotConfig = field(default_factory=ScreenshotConfig)

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Load configuration from environment variables."""
        return cls(
            timeouts=TimeoutConfig(
                navigation=int(os.getenv("CAMOUFOX_TIMEOUT_NAVIGATION", "30000")),
                selector_wait=int(os.getenv("CAMOUFOX_TIMEOUT_SELECTOR", "30000")),
                network_wait=int(os.getenv("CAMOUFOX_TIMEOUT_NETWORK", "30000")),
                element_action=int(os.getenv("CAMOUFOX_TIMEOUT_ACTION", "5000")),
                screenshot=int(os.getenv("CAMOUFOX_TIMEOUT_SCREENSHOT", "10000")),
                js_evaluation=int(os.getenv("CAMOUFOX_TIMEOUT_JS", "5000")),
                browser_launch=int(os.getenv("CAMOUFOX_TIMEOUT_LAUNCH", "60000")),
                page_close=int(os.getenv("CAMOUFOX_TIMEOUT_PAGE_CLOSE", "5000")),
            ),
            network=NetworkConfig(
                capture_by_default=os.getenv("CAMOUFOX_NETWORK_CAPTURE", "true").lower() == "true",
                capture_bodies_by_default=os.getenv("CAMOUFOX_NETWORK_BODIES", "false").lower()
                == "true",
                max_log_size=int(os.getenv("CAMOUFOX_NETWORK_MAX_LOG", "1000")),
                max_body_size=int(os.getenv("CAMOUFOX_NETWORK_MAX_BODY", "10000")),
            ),
            logging=LogConfig(
                level=os.getenv("CAMOUFOX_LOG_LEVEL", "INFO").upper(),  # type: ignore
                format=os.getenv("CAMOUFOX_LOG_FORMAT", "json").lower(),  # type: ignore
                include_timestamps=os.getenv("CAMOUFOX_LOG_TIMESTAMPS", "true").lower() == "true",
                include_caller=os.getenv("CAMOUFOX_LOG_CALLER", "false").lower() == "true",
            ),
            browser=BrowserConfig(
                default_headless=os.getenv("CAMOUFOX_HEADLESS", "true").lower() == "true",
                default_humanize=os.getenv("CAMOUFOX_HUMANIZE", "true").lower() == "true",
                default_viewport_width=int(os.getenv("CAMOUFOX_VIEWPORT_WIDTH", "1920")),
                default_viewport_height=int(os.getenv("CAMOUFOX_VIEWPORT_HEIGHT", "1080")),
                auto_recover=os.getenv("CAMOUFOX_AUTO_RECOVER", "true").lower() == "true",
                max_pages=int(os.getenv("CAMOUFOX_MAX_PAGES", "10")),
            ),
            screenshot=ScreenshotConfig(
                default_dir=os.getenv("CAMOUFOX_SCREENSHOT_DIR", "/tmp/camoufox_screenshots"),
                auto_save=os.getenv("CAMOUFOX_SCREENSHOT_AUTO_SAVE", "true").lower() == "true",
            ),
        )


# Global configuration instance - initialized once at startup
_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Get the global server configuration."""
    global _config
    if _config is None:
        _config = ServerConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset configuration (useful for testing)."""
    global _config
    _config = None
