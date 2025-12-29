"""
Input validation for Camoufox MCP Server.

Provides Pydantic-based validators for all tool inputs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class UrlInput(BaseModel):
    """Validates URL inputs."""

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("URL cannot be empty")

        # Allow special URLs
        if v in ("about:blank", "chrome://newtab"):
            return v

        parsed = urlparse(v)

        # Must have scheme
        if not parsed.scheme:
            raise ValueError(f"URL must have a scheme (http/https): {v}")

        # Only allow http(s) and file schemes
        if parsed.scheme not in ("http", "https", "file"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Allowed: http, https, file")

        # Must have netloc for http(s)
        if parsed.scheme in ("http", "https") and not parsed.netloc:
            raise ValueError(f"URL must have a domain: {v}")

        return v


class SelectorInput(BaseModel):
    """Validates CSS/XPath selector inputs."""

    selector: str

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        if not v:
            raise ValueError("Selector cannot be empty")

        if len(v) > 2000:
            raise ValueError("Selector too long (max 2000 characters)")

        # Basic XPath detection and validation
        if v.startswith("//") or v.startswith("(//"):
            # XPath selector - basic validation
            if v.count("[") != v.count("]"):
                raise ValueError("Unbalanced brackets in XPath selector")
            if v.count("(") != v.count(")"):
                raise ValueError("Unbalanced parentheses in XPath selector")
            return v

        # CSS selector validation
        # Check for common syntax errors
        if v.endswith(","):
            raise ValueError("Selector cannot end with a comma")

        # Check for unbalanced brackets
        if v.count("[") != v.count("]"):
            raise ValueError("Unbalanced brackets in CSS selector")
        if v.count("(") != v.count(")"):
            raise ValueError("Unbalanced parentheses in CSS selector")

        return v


class TimeoutInput(BaseModel):
    """Validates timeout inputs."""

    timeout: int = Field(ge=100, le=300000)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 100:
            raise ValueError("Timeout must be at least 100ms")
        if v > 300000:
            raise ValueError("Timeout cannot exceed 300000ms (5 minutes)")
        return v


class ViewportInput(BaseModel):
    """Validates viewport size inputs."""

    width: int = Field(ge=200, le=7680)
    height: int = Field(ge=200, le=4320)


class FilePathInput(BaseModel):
    """Validates file path inputs."""

    path: str
    must_exist: bool = False
    allowed_extensions: list[str] | None = None

    @model_validator(mode="after")
    def validate_path(self) -> FilePathInput:
        if not self.path:
            raise ValueError("File path cannot be empty")

        # Basic path validation
        path = Path(self.path)

        # Check for path traversal attempts
        try:
            resolved = path.resolve()
            # Ensure path doesn't escape expected directories
            if ".." in self.path:
                raise ValueError("Path traversal not allowed")
        except Exception:
            raise ValueError(f"Invalid path: {self.path}")

        if self.must_exist and not path.exists():
            raise ValueError(f"File does not exist: {self.path}")

        if self.allowed_extensions:
            ext = path.suffix.lower()
            if ext not in self.allowed_extensions:
                raise ValueError(
                    f"Invalid file extension '{ext}'. Allowed: {self.allowed_extensions}"
                )

        return self


class WaitStateInput(BaseModel):
    """Validates wait state inputs."""

    state: Literal["attached", "detached", "visible", "hidden"]


class LoadStateInput(BaseModel):
    """Validates page load state inputs."""

    state: Literal["load", "domcontentloaded", "networkidle", "commit"]


class MouseButtonInput(BaseModel):
    """Validates mouse button inputs."""

    button: Literal["left", "right", "middle"] = "left"


class ProxyInput(BaseModel):
    """Validates proxy configuration inputs."""

    server: str
    username: str | None = None
    password: str | None = None

    @field_validator("server")
    @classmethod
    def validate_server(cls, v: str) -> str:
        if not v:
            raise ValueError("Proxy server cannot be empty")

        # Basic proxy URL validation
        parsed = urlparse(v)
        if not parsed.scheme:
            # Allow just host:port
            if ":" not in v:
                raise ValueError("Proxy must include port (host:port or full URL)")
            return v

        if parsed.scheme not in ("http", "https", "socks4", "socks5"):
            raise ValueError(f"Invalid proxy scheme: {parsed.scheme}")

        return v


class JavaScriptInput(BaseModel):
    """Validates JavaScript code inputs."""

    expression: str

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v: str) -> str:
        if not v:
            raise ValueError("JavaScript expression cannot be empty")

        if len(v) > 100000:
            raise ValueError("JavaScript expression too long (max 100KB)")

        # Check for potential infinite loops (basic heuristic)
        if re.search(r"while\s*\(\s*true\s*\)", v):
            raise ValueError("Potential infinite loop detected (while(true))")

        if re.search(r"for\s*\(\s*;\s*;\s*\)", v):
            raise ValueError("Potential infinite loop detected (for(;;))")

        return v


class CookieInput(BaseModel):
    """Validates cookie inputs."""

    name: str = Field(min_length=1, max_length=256)
    value: str = Field(max_length=4096)
    url: str | None = None
    domain: str | None = None
    path: str = "/"
    expires: int | None = None
    http_only: bool = False
    secure: bool = False

    @model_validator(mode="after")
    def validate_cookie(self) -> CookieInput:
        if not self.url and not self.domain:
            raise ValueError("Either url or domain must be specified")

        if self.url:
            # Validate URL
            UrlInput(url=self.url)

        if self.expires is not None and self.expires < 0:
            raise ValueError("Cookie expiration must be positive")

        return self


class ScrollInput(BaseModel):
    """Validates scroll inputs."""

    x: int = Field(ge=-100000, le=100000)
    y: int = Field(ge=-100000, le=100000)


class ClickInput(BaseModel):
    """Validates click inputs."""

    selector: str
    button: Literal["left", "right", "middle"] = "left"
    click_count: int = Field(ge=1, le=3, default=1)
    delay: int = Field(ge=0, le=5000, default=0)

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        return SelectorInput(selector=v).selector


class TypeTextInput(BaseModel):
    """Validates text input parameters."""

    selector: str
    text: str = Field(max_length=100000)
    delay: int = Field(ge=0, le=1000, default=50)

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        return SelectorInput(selector=v).selector


# Validation helper functions


def validate_url(url: str) -> str:
    """Validate a URL and return it if valid."""
    return UrlInput(url=url).url


def validate_selector(selector: str) -> str:
    """Validate a selector and return it if valid."""
    return SelectorInput(selector=selector).selector


def validate_timeout(timeout: int) -> int:
    """Validate a timeout value and return it if valid."""
    return TimeoutInput(timeout=timeout).timeout


def validate_viewport(width: int, height: int) -> tuple[int, int]:
    """Validate viewport dimensions and return them if valid."""
    validated = ViewportInput(width=width, height=height)
    return validated.width, validated.height


def validate_file_path(
    path: str,
    must_exist: bool = False,
    allowed_extensions: list[str] | None = None,
) -> str:
    """Validate a file path and return it if valid."""
    return FilePathInput(
        path=path,
        must_exist=must_exist,
        allowed_extensions=allowed_extensions,
    ).path


def validate_javascript(expression: str) -> str:
    """Validate JavaScript code and return it if valid."""
    return JavaScriptInput(expression=expression).expression


def safe_validate(validator_func: callable, *args: Any, **kwargs: Any) -> tuple[bool, Any]:
    """
    Safely validate input, returning (success, result_or_error).

    Usage:
        valid, result = safe_validate(validate_url, user_input)
        if not valid:
            return f"Invalid input: {result}"
    """
    try:
        result = validator_func(*args, **kwargs)
        return True, result
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"
