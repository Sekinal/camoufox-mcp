"""
Tests for input validation.
"""

import pytest

from src.camoufox_mcp.validation import (
    validate_url,
    validate_selector,
    validate_timeout,
    validate_viewport,
    validate_file_path,
    validate_javascript,
    safe_validate,
    UrlInput,
    SelectorInput,
    TimeoutInput,
)


class TestUrlValidation:
    """Tests for URL validation."""

    def test_valid_http_url(self):
        """Test valid HTTP URLs."""
        assert validate_url("http://example.com") == "http://example.com"
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("https://example.com/path?query=1") == "https://example.com/path?query=1"

    def test_valid_special_urls(self):
        """Test special URLs."""
        assert validate_url("about:blank") == "about:blank"

    def test_invalid_url_no_scheme(self):
        """Test URL without scheme is rejected."""
        with pytest.raises(ValueError, match="must have a scheme"):
            validate_url("example.com")

    def test_invalid_url_bad_scheme(self):
        """Test URL with bad scheme is rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("ftp://example.com")

    def test_empty_url(self):
        """Test empty URL is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_url("")


class TestSelectorValidation:
    """Tests for selector validation."""

    def test_valid_css_selector(self):
        """Test valid CSS selectors."""
        assert validate_selector("#id") == "#id"
        assert validate_selector(".class") == ".class"
        assert validate_selector("div > p") == "div > p"
        assert validate_selector("[data-testid='test']") == "[data-testid='test']"

    def test_valid_xpath_selector(self):
        """Test valid XPath selectors."""
        assert validate_selector("//div") == "//div"
        assert validate_selector("//div[@class='test']") == "//div[@class='test']"
        assert validate_selector("(//div)[1]") == "(//div)[1]"

    def test_empty_selector(self):
        """Test empty selector is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_selector("")

    def test_selector_too_long(self):
        """Test selector exceeding max length."""
        with pytest.raises(ValueError, match="too long"):
            validate_selector("a" * 2001)

    def test_unbalanced_brackets(self):
        """Test unbalanced brackets are rejected."""
        with pytest.raises(ValueError, match="Unbalanced brackets"):
            validate_selector("[data-test='value'")


class TestTimeoutValidation:
    """Tests for timeout validation."""

    def test_valid_timeout(self):
        """Test valid timeout values."""
        assert validate_timeout(100) == 100
        assert validate_timeout(30000) == 30000
        assert validate_timeout(300000) == 300000

    def test_timeout_too_small(self):
        """Test timeout below minimum."""
        with pytest.raises((ValueError, Exception), match="greater than or equal to 100"):
            validate_timeout(50)

    def test_timeout_too_large(self):
        """Test timeout above maximum."""
        with pytest.raises((ValueError, Exception), match="less than or equal to 300000"):
            validate_timeout(400000)


class TestViewportValidation:
    """Tests for viewport validation."""

    def test_valid_viewport(self):
        """Test valid viewport dimensions."""
        width, height = validate_viewport(1920, 1080)
        assert width == 1920
        assert height == 1080

    def test_minimum_viewport(self):
        """Test minimum viewport dimensions."""
        width, height = validate_viewport(200, 200)
        assert width == 200
        assert height == 200

    def test_viewport_too_small(self):
        """Test viewport below minimum."""
        with pytest.raises(ValueError):
            validate_viewport(100, 100)


class TestJavaScriptValidation:
    """Tests for JavaScript validation."""

    def test_valid_expression(self):
        """Test valid JavaScript expressions."""
        assert validate_javascript("1 + 1") == "1 + 1"
        assert validate_javascript("document.title") == "document.title"
        assert validate_javascript("() => 'test'") == "() => 'test'"

    def test_empty_expression(self):
        """Test empty expression is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_javascript("")

    def test_infinite_loop_while(self):
        """Test infinite loop detection (while)."""
        with pytest.raises(ValueError, match="infinite loop"):
            validate_javascript("while(true) { console.log('x'); }")

    def test_infinite_loop_for(self):
        """Test infinite loop detection (for)."""
        with pytest.raises(ValueError, match="infinite loop"):
            validate_javascript("for(;;) { break; }")


class TestSafeValidate:
    """Tests for safe_validate helper."""

    def test_successful_validation(self):
        """Test successful validation returns (True, result)."""
        success, result = safe_validate(validate_url, "https://example.com")
        assert success is True
        assert result == "https://example.com"

    def test_failed_validation(self):
        """Test failed validation returns (False, error)."""
        success, error = safe_validate(validate_url, "invalid")
        assert success is False
        assert "scheme" in error.lower()

    def test_exception_handling(self):
        """Test that exceptions are caught."""
        def failing_validator(x):
            raise RuntimeError("Test error")

        success, error = safe_validate(failing_validator, "test")
        assert success is False
        assert "error" in error.lower()
