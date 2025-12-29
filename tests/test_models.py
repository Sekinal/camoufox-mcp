"""
Comprehensive tests for data models.

Tests all dataclasses, serialization, factory methods, and edge cases.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.camoufox_mcp.models import (
    AntiBotDetectionResult,
    BrowserInfo,
    ElementInfo,
    NetworkEntry,
    NetworkPatternAnalysis,
    PageInfo,
    PageStructureAnalysis,
    SelectorTestResult,
    ToolResult,
)


class TestNetworkEntry:
    """Tests for NetworkEntry dataclass."""

    def test_create_minimal(self):
        """Create with required fields only."""
        entry = NetworkEntry(url="https://example.com", method="GET")
        assert entry.url == "https://example.com"
        assert entry.method == "GET"
        assert entry.status is None
        assert entry.request_headers == {}
        assert entry.response_headers == {}
        assert entry.request_body is None
        assert entry.response_body is None
        assert entry.resource_type == ""
        assert entry.timing == {}
        assert entry.duration_ms is None
        assert isinstance(entry.timestamp, datetime)

    def test_create_full(self):
        """Create with all fields."""
        ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = NetworkEntry(
            url="https://api.example.com/data",
            method="POST",
            status=200,
            request_headers={"Content-Type": "application/json"},
            response_headers={"X-Request-Id": "abc123"},
            request_body='{"key": "value"}',
            response_body='{"result": "success"}',
            resource_type="xhr",
            timing={"requestStart": 100, "responseEnd": 250},
            timestamp=ts,
            duration_ms=150.5,
        )
        assert entry.status == 200
        assert entry.resource_type == "xhr"
        assert entry.duration_ms == 150.5

    def test_to_dict_with_bodies(self):
        """Test serialization with bodies included."""
        entry = NetworkEntry(
            url="https://example.com",
            method="GET",
            status=200,
            request_body="request data",
            response_body="response data",
        )
        result = entry.to_dict(include_bodies=True)
        assert result["request_body"] == "request data"
        assert result["response_body"] == "response data"

    def test_to_dict_without_bodies(self):
        """Test serialization without bodies."""
        entry = NetworkEntry(
            url="https://example.com",
            method="GET",
            request_body="request data",
            response_body="response data",
        )
        result = entry.to_dict(include_bodies=False)
        assert "request_body" not in result
        assert "response_body" not in result

    def test_to_dict_truncates_large_body(self):
        """Test that large response bodies are truncated."""
        large_body = "x" * 1000
        entry = NetworkEntry(
            url="https://example.com",
            method="GET",
            response_body=large_body,
        )
        result = entry.to_dict(include_bodies=True, max_body_size=100)
        assert len(result["response_body"]) == 100

    def test_to_dict_includes_timing(self):
        """Test that timing is included when present."""
        entry = NetworkEntry(
            url="https://example.com",
            method="GET",
            timing={"dns": 10, "connect": 50},
        )
        result = entry.to_dict()
        assert result["timing"] == {"dns": 10, "connect": 50}

    def test_to_dict_excludes_empty_timing(self):
        """Test that empty timing is not included."""
        entry = NetworkEntry(url="https://example.com", method="GET")
        result = entry.to_dict()
        assert "timing" not in result

    def test_timestamp_serialization(self):
        """Test timestamp is properly serialized to ISO format."""
        ts = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        entry = NetworkEntry(url="https://example.com", method="GET", timestamp=ts)
        result = entry.to_dict()
        assert result["timestamp"] == "2025-06-15T10:30:00+00:00"


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_create_success(self):
        """Create a successful result."""
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_create_failure(self):
        """Create a failed result."""
        result = ToolResult(success=False, error="Something went wrong", error_type="ValueError")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.error_type == "ValueError"

    def test_ok_factory(self):
        """Test the ok() factory method."""
        result = ToolResult.ok(data="test data", duration_ms=150.0)
        assert result.success is True
        assert result.data == "test data"
        assert result.duration_ms == 150.0

    def test_ok_factory_no_data(self):
        """Test ok() with no data."""
        result = ToolResult.ok()
        assert result.success is True
        assert result.data is None

    def test_fail_factory(self):
        """Test the fail() factory method."""
        result = ToolResult.fail("Error message", error_type="TimeoutError")
        assert result.success is False
        assert result.error == "Error message"
        assert result.error_type == "TimeoutError"

    def test_fail_factory_no_type(self):
        """Test fail() without error type."""
        result = ToolResult.fail("Error message")
        assert result.success is False
        assert result.error == "Error message"
        assert result.error_type is None

    def test_to_dict_success(self):
        """Test to_dict for successful result."""
        result = ToolResult.ok(data={"items": [1, 2, 3]}, duration_ms=50.0)
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == {"items": [1, 2, 3]}
        assert d["duration_ms"] == 50.0
        assert "error" not in d

    def test_to_dict_failure(self):
        """Test to_dict for failed result."""
        result = ToolResult.fail("Timeout", error_type="TimeoutError", duration_ms=30000.0)
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Timeout"
        assert d["error_type"] == "TimeoutError"
        assert "data" not in d

    def test_to_json(self):
        """Test JSON serialization."""
        result = ToolResult.ok(data="test")
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"] == "test"

    def test_to_json_with_complex_data(self):
        """Test JSON serialization with nested data."""
        result = ToolResult.ok(data={
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        })
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["data"]["nested"]["key"] == "value"


class TestPageInfo:
    """Tests for PageInfo dataclass."""

    def test_create_minimal(self):
        """Create with required fields."""
        info = PageInfo(page_id="main", url="https://example.com")
        assert info.page_id == "main"
        assert info.url == "https://example.com"
        assert info.title is None
        assert info.is_active is False

    def test_create_full(self):
        """Create with all fields."""
        info = PageInfo(
            page_id="tab-1",
            url="https://example.com/page",
            title="Example Page",
            is_active=True,
        )
        assert info.title == "Example Page"
        assert info.is_active is True


class TestBrowserInfo:
    """Tests for BrowserInfo dataclass."""

    def test_create_stopped(self):
        """Create stopped browser info."""
        info = BrowserInfo(status="stopped")
        assert info.status == "stopped"
        assert info.pages == []
        assert info.active_page_id is None

    def test_create_running(self):
        """Create running browser info with pages."""
        pages = [
            PageInfo(page_id="main", url="https://example.com", is_active=True),
            PageInfo(page_id="tab-1", url="https://other.com"),
        ]
        info = BrowserInfo(
            status="running",
            pages=pages,
            active_page_id="main",
            network_capture_enabled=True,
            capture_bodies=True,
            network_log_size=150,
            uptime_seconds=3600.5,
            total_requests=500,
            total_errors=3,
        )
        assert info.status == "running"
        assert len(info.pages) == 2
        assert info.network_capture_enabled is True
        assert info.uptime_seconds == 3600.5


class TestElementInfo:
    """Tests for ElementInfo dataclass."""

    def test_create_minimal(self):
        """Create with required fields only."""
        info = ElementInfo(tag_name="div")
        assert info.tag_name == "div"
        assert info.id is None
        assert info.is_visible is True
        assert info.attributes == []

    def test_create_full(self):
        """Create with all fields."""
        info = ElementInfo(
            tag_name="input",
            id="username",
            class_name="form-control",
            name="user",
            type="text",
            value="john_doe",
            is_visible=True,
            bounding_rect={"x": 100, "y": 200, "width": 300, "height": 40},
            attributes=[{"name": "placeholder", "value": "Enter username"}],
        )
        assert info.type == "text"
        assert info.value == "john_doe"
        assert info.bounding_rect["width"] == 300

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        info = ElementInfo(tag_name="a", href="https://example.com")
        d = info.to_dict()
        assert "tag_name" in d
        assert "href" in d
        assert "id" not in d  # None values excluded
        assert "src" not in d

    def test_to_dict_includes_false(self):
        """Test to_dict includes False values (not None)."""
        info = ElementInfo(tag_name="div", is_visible=False)
        d = info.to_dict()
        assert d["is_visible"] is False


class TestAntiBotDetectionResult:
    """Tests for AntiBotDetectionResult dataclass."""

    def test_no_protection_detected(self):
        """Test when no protection is detected."""
        result = AntiBotDetectionResult()
        assert result.any_protection_detected is False
        assert result.cloudflare_detected is False
        assert result.akamai_detected is False

    def test_cloudflare_detected(self):
        """Test Cloudflare detection."""
        result = AntiBotDetectionResult(
            cloudflare_detected=True,
            cloudflare_indicators=["cf-ray header", "challenge page"],
        )
        assert result.any_protection_detected is True
        assert result.cloudflare_detected is True
        assert len(result.cloudflare_indicators) == 2

    def test_multiple_protections(self):
        """Test multiple protections detected."""
        result = AntiBotDetectionResult(
            cloudflare_detected=True,
            akamai_detected=True,
            captcha_detected=True,
            captcha_type="recaptcha_v3",
        )
        assert result.any_protection_detected is True
        assert result.captcha_type == "recaptcha_v3"

    def test_other_protections(self):
        """Test other_protections triggers any_protection_detected."""
        result = AntiBotDetectionResult(
            other_protections=["Custom WAF detected"],
        )
        assert result.any_protection_detected is True

    def test_to_dict(self):
        """Test serialization to dict."""
        result = AntiBotDetectionResult(
            datadome_detected=True,
            datadome_indicators=["datadome cookie found"],
        )
        d = result.to_dict()
        assert d["datadome_detected"] is True
        assert d["datadome_indicators"] == ["datadome cookie found"]


class TestPageStructureAnalysis:
    """Tests for PageStructureAnalysis dataclass."""

    def test_default_values(self):
        """Test default values."""
        analysis = PageStructureAnalysis()
        assert analysis.total_elements == 0
        assert analysis.element_counts == {}
        assert analysis.framework_detected is None

    def test_with_data(self):
        """Test with analysis data."""
        analysis = PageStructureAnalysis(
            total_elements=1500,
            element_counts={"div": 500, "span": 300, "p": 200},
            shadow_dom_count=5,
            iframe_count=2,
            framework_detected="React",
            lazy_load_indicators=["data-lazy", "loading=\"lazy\""],
        )
        assert analysis.total_elements == 1500
        assert analysis.element_counts["div"] == 500
        assert analysis.framework_detected == "React"

    def test_to_dict(self):
        """Test serialization."""
        analysis = PageStructureAnalysis(
            total_elements=100,
            form_count=3,
            input_count=15,
        )
        d = analysis.to_dict()
        assert d["total_elements"] == 100
        assert d["form_count"] == 3


class TestNetworkPatternAnalysis:
    """Tests for NetworkPatternAnalysis dataclass."""

    def test_default_values(self):
        """Test default values."""
        analysis = NetworkPatternAnalysis()
        assert analysis.api_endpoints == []
        assert analysis.graphql_endpoints == []
        assert analysis.total_transfer_size == 0

    def test_with_data(self):
        """Test with pattern data."""
        analysis = NetworkPatternAnalysis(
            api_endpoints=[
                {"url": "/api/v1/users", "methods": ["GET", "POST"]},
                {"url": "/api/v1/products", "methods": ["GET"]},
            ],
            graphql_endpoints=["https://api.example.com/graphql"],
            websocket_urls=["wss://ws.example.com/socket"],
            authentication_patterns=["Bearer token", "Cookie auth"],
            third_party_domains=["analytics.google.com", "cdn.cloudflare.com"],
            resource_stats={"xhr": 50, "script": 30, "image": 100},
            total_transfer_size=5_000_000,
        )
        assert len(analysis.api_endpoints) == 2
        assert analysis.total_transfer_size == 5_000_000

    def test_to_dict(self):
        """Test serialization."""
        analysis = NetworkPatternAnalysis(
            graphql_endpoints=["/graphql"],
        )
        d = analysis.to_dict()
        assert d["graphql_endpoints"] == ["/graphql"]


class TestSelectorTestResult:
    """Tests for SelectorTestResult dataclass."""

    def test_no_matches(self):
        """Test selector with no matches."""
        result = SelectorTestResult(
            selector="div.nonexistent",
            selector_type="css",
            match_count=0,
        )
        assert result.match_count == 0
        assert result.is_unique is False

    def test_unique_match(self):
        """Test unique selector match."""
        result = SelectorTestResult(
            selector="#submit-button",
            selector_type="css",
            match_count=1,
            is_unique=True,
            sample_elements=[{"tag": "button", "id": "submit-button"}],
        )
        assert result.is_unique is True
        assert len(result.sample_elements) == 1

    def test_multiple_matches_with_warnings(self):
        """Test multiple matches with warnings."""
        result = SelectorTestResult(
            selector="button",
            selector_type="css",
            match_count=15,
            warnings=["Selector matches multiple elements", "Consider using ID or unique class"],
            suggestions=["button.submit-btn", "button[type='submit']"],
        )
        assert len(result.warnings) == 2
        assert len(result.suggestions) == 2

    def test_xpath_selector(self):
        """Test XPath selector."""
        result = SelectorTestResult(
            selector="//input[@name='email']",
            selector_type="xpath",
            match_count=1,
            is_unique=True,
        )
        assert result.selector_type == "xpath"

    def test_to_dict(self):
        """Test serialization."""
        result = SelectorTestResult(
            selector="div",
            selector_type="css",
            match_count=50,
        )
        d = result.to_dict()
        assert d["selector"] == "div"
        assert d["match_count"] == 50


class TestModelEdgeCases:
    """Edge case tests for models."""

    def test_network_entry_empty_url(self):
        """Test with empty URL."""
        entry = NetworkEntry(url="", method="GET")
        assert entry.url == ""

    def test_network_entry_unicode_body(self):
        """Test with unicode content."""
        entry = NetworkEntry(
            url="https://example.com",
            method="POST",
            request_body="日本語テスト",
            response_body="Émojis: 🎉🚀",
        )
        result = entry.to_dict()
        assert result["request_body"] == "日本語テスト"
        assert "🎉" in result["response_body"]

    def test_tool_result_with_none_data(self):
        """Test ToolResult with explicit None data."""
        result = ToolResult.ok(data=None)
        d = result.to_dict()
        assert d["data"] is None

    def test_element_info_empty_attributes(self):
        """Test ElementInfo with empty attributes list."""
        info = ElementInfo(tag_name="div", attributes=[])
        d = info.to_dict()
        # Empty list should be excluded (evaluates to False-y but is not None)
        # Actually, empty list is not None, so it should be included
        assert d["attributes"] == []

    def test_browser_info_with_empty_pages(self):
        """Test BrowserInfo with explicitly empty pages."""
        info = BrowserInfo(status="running", pages=[])
        assert info.pages == []

    def test_large_network_entry(self):
        """Test with large headers and body."""
        headers = {f"X-Header-{i}": f"value-{i}" for i in range(100)}
        entry = NetworkEntry(
            url="https://example.com",
            method="GET",
            request_headers=headers,
            response_body="x" * 10000,
        )
        result = entry.to_dict(max_body_size=500)
        assert len(result["request_headers"]) == 100
        assert len(result["response_body"]) == 500
