"""
Data models for Camoufox MCP Server.

Contains dataclasses for network entries, tool results, and other shared types.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class NetworkEntry:
    """Represents a captured network request/response."""

    url: str
    method: str
    status: int | None = None
    request_headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    request_body: str | None = None
    response_body: str | None = None
    resource_type: str = ""
    timing: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float | None = None

    def to_dict(self, include_bodies: bool = True, max_body_size: int = 500) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "resource_type": self.resource_type,
            "request_headers": self.request_headers,
            "response_headers": self.response_headers,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_ms": self.duration_ms,
        }

        if include_bodies:
            result["request_body"] = self.request_body
            if self.response_body:
                result["response_body"] = (
                    self.response_body[:max_body_size]
                    if len(self.response_body) > max_body_size
                    else self.response_body
                )
            else:
                result["response_body"] = None

        if self.timing:
            result["timing"] = self.timing

        return result


@dataclass
class ToolResult:
    """Standardized result from tool execution."""

    success: bool
    data: Any = None
    error: str | None = None
    error_type: str | None = None
    duration_ms: float = 0.0
    tool_name: str = ""
    call_id: str = ""

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "duration_ms": self.duration_ms,
        }

        if self.success:
            result["data"] = self.data
        else:
            result["error"] = self.error
            if self.error_type:
                result["error_type"] = self.error_type

        return result

    @classmethod
    def ok(cls, data: Any = None, **kwargs: Any) -> ToolResult:
        """Create a successful result."""
        return cls(success=True, data=data, **kwargs)

    @classmethod
    def fail(cls, error: str, error_type: str | None = None, **kwargs: Any) -> ToolResult:
        """Create a failed result."""
        return cls(success=False, error=error, error_type=error_type, **kwargs)


@dataclass
class PageInfo:
    """Information about a browser page."""

    page_id: str
    url: str
    title: str | None = None
    is_active: bool = False


@dataclass
class BrowserInfo:
    """Information about the browser session."""

    status: str  # "running", "stopped", "crashed"
    pages: list[PageInfo] = field(default_factory=list)
    active_page_id: str | None = None
    network_capture_enabled: bool = False
    capture_bodies: bool = False
    network_log_size: int = 0
    uptime_seconds: float = 0.0
    total_requests: int = 0
    total_errors: int = 0


@dataclass
class ElementInfo:
    """Detailed information about a DOM element."""

    tag_name: str
    id: str | None = None
    class_name: str | None = None
    name: str | None = None
    type: str | None = None
    value: str | None = None
    href: str | None = None
    src: str | None = None
    inner_text: str | None = None
    inner_html: str | None = None
    is_visible: bool = True
    bounding_rect: dict[str, float] | None = None
    attributes: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AntiBotDetectionResult:
    """Result of anti-bot protection detection."""

    cloudflare_detected: bool = False
    cloudflare_indicators: list[str] = field(default_factory=list)

    akamai_detected: bool = False
    akamai_indicators: list[str] = field(default_factory=list)

    perimeterx_detected: bool = False
    perimeterx_indicators: list[str] = field(default_factory=list)

    datadome_detected: bool = False
    datadome_indicators: list[str] = field(default_factory=list)

    captcha_detected: bool = False
    captcha_type: str | None = None
    captcha_indicators: list[str] = field(default_factory=list)

    other_protections: list[str] = field(default_factory=list)

    @property
    def any_protection_detected(self) -> bool:
        """Check if any protection was detected."""
        return any([
            self.cloudflare_detected,
            self.akamai_detected,
            self.perimeterx_detected,
            self.datadome_detected,
            self.captcha_detected,
            bool(self.other_protections),
        ])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PageStructureAnalysis:
    """Analysis of page DOM structure."""

    total_elements: int = 0
    element_counts: dict[str, int] = field(default_factory=dict)  # Tag -> count
    shadow_dom_count: int = 0
    iframe_count: int = 0
    iframe_nesting_depth: int = 0
    form_count: int = 0
    input_count: int = 0
    link_count: int = 0
    script_count: int = 0
    framework_detected: str | None = None  # React, Vue, Angular, etc.
    lazy_load_indicators: list[str] = field(default_factory=list)
    dynamic_content_markers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NetworkPatternAnalysis:
    """Analysis of network request patterns."""

    api_endpoints: list[dict[str, Any]] = field(default_factory=list)
    graphql_endpoints: list[str] = field(default_factory=list)
    websocket_urls: list[str] = field(default_factory=list)
    authentication_patterns: list[str] = field(default_factory=list)
    third_party_domains: list[str] = field(default_factory=list)
    cdn_domains: list[str] = field(default_factory=list)
    resource_stats: dict[str, int] = field(default_factory=dict)  # Type -> count
    total_transfer_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SelectorTestResult:
    """Result of testing a CSS/XPath selector."""

    selector: str
    selector_type: str  # "css" or "xpath"
    match_count: int
    sample_elements: list[dict[str, Any]] = field(default_factory=list)
    is_unique: bool = False
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
