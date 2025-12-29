"""
Camoufox MCP Server - Browser automation and web scraping tools for Claude.

This server provides comprehensive browser control, network analysis,
and page interaction capabilities using Camoufox (anti-detect Firefox).
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import FastMCP
from camoufox.async_api import AsyncCamoufox
from playwright.async_api import Page, BrowserContext, Response, Request

# Configure logging (never use print in stdio servers!)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("camoufox")


@dataclass
class NetworkEntry:
    """Represents a captured network request/response."""
    url: str
    method: str
    status: int | None = None
    request_headers: dict = field(default_factory=dict)
    response_headers: dict = field(default_factory=dict)
    request_body: str | None = None
    response_body: str | None = None
    resource_type: str = ""
    timing: dict = field(default_factory=dict)


class BrowserSession:
    """Manages a Camoufox browser session with network capture."""

    def __init__(self):
        self.browser: AsyncCamoufox | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.pages: dict[str, Page] = {}
        self.network_log: list[NetworkEntry] = []
        self.capture_network: bool = True
        self.capture_bodies: bool = False
        self._browser_cm = None

    async def launch(
        self,
        headless: bool = False,
        proxy: dict | None = None,
        os_type: str | list[str] | None = None,
        humanize: bool | float = False,
        geoip: bool = False,
        block_images: bool = False,
        locale: str | None = None,
    ) -> str:
        """Launch a new browser session."""
        if self.browser is not None:
            return "Browser already running. Close it first with close_browser."

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

        self._browser_cm = AsyncCamoufox(**kwargs)
        self.browser = await self._browser_cm.__aenter__()
        self.page = await self.browser.new_page()
        self.pages["main"] = self.page

        # Set up network capture
        await self._setup_network_capture(self.page)

        return "Browser launched successfully. Main page created."

    async def _setup_network_capture(self, page: Page):
        """Set up network request/response capture for a page."""

        async def on_request(request: Request):
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
            self.network_log.append(entry)

        async def on_response(response: Response):
            if not self.capture_network:
                return
            # Find matching request entry
            for entry in reversed(self.network_log):
                if entry.url == response.url and entry.status is None:
                    entry.status = response.status
                    entry.response_headers = dict(response.headers)
                    if self.capture_bodies:
                        try:
                            entry.response_body = await response.text()
                        except Exception:
                            pass
                    try:
                        timing = response.request.timing
                        entry.timing = timing if isinstance(timing, dict) else {}
                    except Exception:
                        pass
                    break

        page.on("request", on_request)
        page.on("response", on_response)

    async def close(self):
        """Close the browser session."""
        if self._browser_cm:
            await self._browser_cm.__aexit__(None, None, None)
        self.browser = None
        self.context = None
        self.page = None
        self.pages.clear()
        self.network_log.clear()
        self._browser_cm = None


# Global browser session
session = BrowserSession()


# ============================================================================
# Browser Management Tools
# ============================================================================

@mcp.tool()
async def launch_browser(
    headless: bool = False,
    proxy_server: str | None = None,
    proxy_username: str | None = None,
    proxy_password: str | None = None,
    os_type: str = "random",
    humanize: bool = True,
    geoip: bool = False,
    block_images: bool = False,
    locale: str | None = None,
) -> str:
    """
    Launch a Camoufox browser with anti-detect capabilities.

    Args:
        headless: Run browser in headless mode (default: False for debugging)
        proxy_server: Proxy server URL (e.g., "http://proxy.example.com:8080")
        proxy_username: Proxy authentication username
        proxy_password: Proxy authentication password
        os_type: OS to spoof - "windows", "macos", "linux", or "random"
        humanize: Enable human-like cursor movement (True or max duration in seconds)
        geoip: Auto-detect location from IP for geolocation spoofing
        block_images: Block image loading for faster scraping
        locale: Browser locale (e.g., "en-US")

    Returns:
        Status message about browser launch
    """
    proxy = None
    if proxy_server:
        proxy = {"server": proxy_server}
        if proxy_username:
            proxy["username"] = proxy_username
        if proxy_password:
            proxy["password"] = proxy_password

    os_setting = None if os_type == "random" else os_type

    return await session.launch(
        headless=headless,
        proxy=proxy,
        os_type=os_setting,
        humanize=humanize,
        geoip=geoip,
        block_images=block_images,
        locale=locale,
    )


@mcp.tool()
async def close_browser() -> str:
    """
    Close the browser and clean up all resources.

    Returns:
        Confirmation message
    """
    await session.close()
    return "Browser closed successfully."


@mcp.tool()
async def new_page(page_id: str = "new") -> str:
    """
    Create a new browser tab/page.

    Args:
        page_id: Identifier for this page (used to switch between pages)

    Returns:
        Status message
    """
    if not session.browser:
        return "Error: Browser not launched. Call launch_browser first."

    page = await session.browser.new_page()
    await session._setup_network_capture(page)
    session.pages[page_id] = page
    session.page = page
    return f"New page created with id '{page_id}' and set as active."


@mcp.tool()
async def switch_page(page_id: str) -> str:
    """
    Switch to a different page/tab.

    Args:
        page_id: The page identifier to switch to

    Returns:
        Status message
    """
    if page_id not in session.pages:
        available = list(session.pages.keys())
        return f"Error: Page '{page_id}' not found. Available: {available}"

    session.page = session.pages[page_id]
    return f"Switched to page '{page_id}'."


@mcp.tool()
async def list_pages() -> str:
    """
    List all open pages/tabs.

    Returns:
        JSON list of page IDs and their URLs
    """
    if not session.pages:
        return "No pages open."

    pages_info = []
    for page_id, page in session.pages.items():
        try:
            url = page.url
        except Exception:
            url = "unknown"
        pages_info.append({"id": page_id, "url": url})

    return json.dumps(pages_info, indent=2)


# ============================================================================
# Navigation Tools
# ============================================================================

@mcp.tool()
async def goto(url: str, wait_until: str = "load") -> str:
    """
    Navigate to a URL.

    Args:
        url: The URL to navigate to
        wait_until: When to consider navigation complete - "load", "domcontentloaded", "networkidle", or "commit"

    Returns:
        Navigation result with final URL and status
    """
    if not session.page:
        return "Error: No active page. Launch browser first."

    try:
        response = await session.page.goto(url, wait_until=wait_until)
        status = response.status if response else "unknown"
        final_url = session.page.url
        return json.dumps({
            "success": True,
            "status": status,
            "url": final_url,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def reload(wait_until: str = "load") -> str:
    """
    Reload the current page.

    Args:
        wait_until: When to consider reload complete

    Returns:
        Reload result
    """
    if not session.page:
        return "Error: No active page."

    await session.page.reload(wait_until=wait_until)
    return f"Page reloaded. URL: {session.page.url}"


@mcp.tool()
async def go_back() -> str:
    """Navigate back in history."""
    if not session.page:
        return "Error: No active page."
    await session.page.go_back()
    return f"Navigated back. URL: {session.page.url}"


@mcp.tool()
async def go_forward() -> str:
    """Navigate forward in history."""
    if not session.page:
        return "Error: No active page."
    await session.page.go_forward()
    return f"Navigated forward. URL: {session.page.url}"


@mcp.tool()
async def get_url() -> str:
    """Get the current page URL."""
    if not session.page:
        return "Error: No active page."
    return session.page.url


# ============================================================================
# Page Interaction Tools
# ============================================================================

@mcp.tool()
async def click(
    selector: str,
    button: str = "left",
    click_count: int = 1,
    delay: int = 0,
) -> str:
    """
    Click an element on the page.

    Args:
        selector: CSS selector, XPath (starting with //), or text selector
        button: Mouse button - "left", "right", or "middle"
        click_count: Number of clicks (2 for double-click)
        delay: Delay between mousedown and mouseup in milliseconds

    Returns:
        Click result
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.click(selector, button=button, click_count=click_count, delay=delay)
        return f"Clicked element: {selector}"
    except Exception as e:
        return f"Error clicking '{selector}': {str(e)}"


@mcp.tool()
async def fill(selector: str, value: str) -> str:
    """
    Fill a text input or textarea with a value.

    Args:
        selector: CSS selector for the input element
        value: Text to fill in

    Returns:
        Fill result
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.fill(selector, value)
        return f"Filled '{selector}' with value."
    except Exception as e:
        return f"Error filling '{selector}': {str(e)}"


@mcp.tool()
async def type_text(selector: str, text: str, delay: int = 50) -> str:
    """
    Type text character by character (more human-like than fill).

    Args:
        selector: CSS selector for the input element
        text: Text to type
        delay: Delay between keystrokes in milliseconds

    Returns:
        Type result
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.type(selector, text, delay=delay)
        return f"Typed text into '{selector}'."
    except Exception as e:
        return f"Error typing into '{selector}': {str(e)}"


@mcp.tool()
async def press_key(key: str, selector: str | None = None) -> str:
    """
    Press a keyboard key.

    Args:
        key: Key to press (e.g., "Enter", "Tab", "Escape", "ArrowDown", "Control+a")
        selector: Optional selector to focus first

    Returns:
        Key press result
    """
    if not session.page:
        return "Error: No active page."

    try:
        if selector:
            await session.page.press(selector, key)
        else:
            await session.page.keyboard.press(key)
        return f"Pressed key: {key}"
    except Exception as e:
        return f"Error pressing key '{key}': {str(e)}"


@mcp.tool()
async def select_option(selector: str, value: str | None = None, label: str | None = None, index: int | None = None) -> str:
    """
    Select an option from a dropdown/select element.

    Args:
        selector: CSS selector for the select element
        value: Option value to select
        label: Option label/text to select
        index: Option index to select (0-based)

    Returns:
        Selection result
    """
    if not session.page:
        return "Error: No active page."

    try:
        if value is not None:
            await session.page.select_option(selector, value=value)
        elif label is not None:
            await session.page.select_option(selector, label=label)
        elif index is not None:
            await session.page.select_option(selector, index=index)
        else:
            return "Error: Must provide value, label, or index."
        return f"Selected option in '{selector}'."
    except Exception as e:
        return f"Error selecting option: {str(e)}"


@mcp.tool()
async def check(selector: str) -> str:
    """
    Check a checkbox or radio button.

    Args:
        selector: CSS selector for the checkbox/radio

    Returns:
        Check result
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.check(selector)
        return f"Checked: {selector}"
    except Exception as e:
        return f"Error checking '{selector}': {str(e)}"


@mcp.tool()
async def uncheck(selector: str) -> str:
    """
    Uncheck a checkbox.

    Args:
        selector: CSS selector for the checkbox

    Returns:
        Uncheck result
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.uncheck(selector)
        return f"Unchecked: {selector}"
    except Exception as e:
        return f"Error unchecking '{selector}': {str(e)}"


@mcp.tool()
async def hover(selector: str) -> str:
    """
    Hover over an element.

    Args:
        selector: CSS selector for the element

    Returns:
        Hover result
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.hover(selector)
        return f"Hovering over: {selector}"
    except Exception as e:
        return f"Error hovering '{selector}': {str(e)}"


@mcp.tool()
async def scroll(
    x: int = 0,
    y: int = 0,
    selector: str | None = None,
) -> str:
    """
    Scroll the page or an element.

    Args:
        x: Horizontal scroll amount in pixels
        y: Vertical scroll amount in pixels (positive = down)
        selector: Optional element to scroll into view instead

    Returns:
        Scroll result
    """
    if not session.page:
        return "Error: No active page."

    try:
        if selector:
            await session.page.locator(selector).scroll_into_view_if_needed()
            return f"Scrolled '{selector}' into view."
        else:
            await session.page.evaluate(f"window.scrollBy({x}, {y})")
            return f"Scrolled by ({x}, {y})."
    except Exception as e:
        return f"Error scrolling: {str(e)}"


@mcp.tool()
async def upload_file(selector: str, file_path: str) -> str:
    """
    Upload a file to a file input.

    Args:
        selector: CSS selector for the file input
        file_path: Path to the file to upload

    Returns:
        Upload result
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.set_input_files(selector, file_path)
        return f"Uploaded file to '{selector}'."
    except Exception as e:
        return f"Error uploading file: {str(e)}"


# ============================================================================
# Content Extraction Tools
# ============================================================================

@mcp.tool()
async def get_text(selector: str | None = None) -> str:
    """
    Get text content from an element or the entire page.

    Args:
        selector: CSS selector (if None, gets all page text)

    Returns:
        Text content
    """
    if not session.page:
        return "Error: No active page."

    try:
        if selector:
            return await session.page.locator(selector).inner_text()
        else:
            return await session.page.locator("body").inner_text()
    except Exception as e:
        return f"Error getting text: {str(e)}"


@mcp.tool()
async def get_html(selector: str | None = None, outer: bool = True) -> str:
    """
    Get HTML content from an element or the entire page.

    Args:
        selector: CSS selector (if None, gets full page HTML)
        outer: If True, includes the element itself; if False, only inner HTML

    Returns:
        HTML content
    """
    if not session.page:
        return "Error: No active page."

    try:
        if selector:
            if outer:
                return await session.page.locator(selector).evaluate("el => el.outerHTML")
            else:
                return await session.page.locator(selector).inner_html()
        else:
            return await session.page.content()
    except Exception as e:
        return f"Error getting HTML: {str(e)}"


@mcp.tool()
async def get_attribute(selector: str, attribute: str) -> str:
    """
    Get an attribute value from an element.

    Args:
        selector: CSS selector for the element
        attribute: Attribute name (e.g., "href", "src", "class")

    Returns:
        Attribute value or null
    """
    if not session.page:
        return "Error: No active page."

    try:
        value = await session.page.locator(selector).get_attribute(attribute)
        return value if value is not None else "null"
    except Exception as e:
        return f"Error getting attribute: {str(e)}"


@mcp.tool()
async def query_selector_all(selector: str, extract: str = "text") -> str:
    """
    Find all elements matching a selector and extract data.

    Args:
        selector: CSS selector
        extract: What to extract - "text", "html", or an attribute name

    Returns:
        JSON array of extracted values
    """
    if not session.page:
        return "Error: No active page."

    try:
        elements = await session.page.locator(selector).all()
        results = []
        for el in elements:
            if extract == "text":
                results.append(await el.inner_text())
            elif extract == "html":
                results.append(await el.inner_html())
            else:
                results.append(await el.get_attribute(extract))
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error querying elements: {str(e)}"


@mcp.tool()
async def get_page_title() -> str:
    """Get the page title."""
    if not session.page:
        return "Error: No active page."
    return await session.page.title()


# ============================================================================
# Screenshot & Visual Tools
# ============================================================================

@mcp.tool()
async def screenshot(
    path: str | None = None,
    full_page: bool = False,
    selector: str | None = None,
) -> str:
    """
    Take a screenshot of the page or an element.

    Args:
        path: File path to save screenshot (if None, returns base64)
        full_page: Capture the full scrollable page
        selector: CSS selector to screenshot specific element

    Returns:
        Path to saved file or base64-encoded image
    """
    if not session.page:
        return "Error: No active page."

    try:
        if selector:
            screenshot_bytes = await session.page.locator(selector).screenshot()
        else:
            screenshot_bytes = await session.page.screenshot(full_page=full_page)

        if path:
            with open(path, "wb") as f:
                f.write(screenshot_bytes)
            return f"Screenshot saved to: {path}"
        else:
            return f"data:image/png;base64,{base64.b64encode(screenshot_bytes).decode()}"
    except Exception as e:
        return f"Error taking screenshot: {str(e)}"


@mcp.tool()
async def get_viewport_size() -> str:
    """Get the current viewport size."""
    if not session.page:
        return "Error: No active page."
    size = session.page.viewport_size
    return json.dumps(size)


@mcp.tool()
async def set_viewport_size(width: int, height: int) -> str:
    """
    Set the viewport size.

    Args:
        width: Viewport width in pixels
        height: Viewport height in pixels

    Returns:
        Confirmation
    """
    if not session.page:
        return "Error: No active page."
    await session.page.set_viewport_size({"width": width, "height": height})
    return f"Viewport set to {width}x{height}."


# ============================================================================
# Network Analysis Tools
# ============================================================================

@mcp.tool()
async def get_network_log(
    url_filter: str | None = None,
    method_filter: str | None = None,
    status_filter: int | None = None,
    limit: int = 50,
) -> str:
    """
    Get captured network requests/responses.

    Args:
        url_filter: Filter by URL substring
        method_filter: Filter by HTTP method (GET, POST, etc.)
        status_filter: Filter by status code
        limit: Maximum number of entries to return

    Returns:
        JSON array of network entries
    """
    entries = session.network_log.copy()

    if url_filter:
        entries = [e for e in entries if url_filter.lower() in e.url.lower()]
    if method_filter:
        entries = [e for e in entries if e.method.upper() == method_filter.upper()]
    if status_filter:
        entries = [e for e in entries if e.status == status_filter]

    entries = entries[-limit:]

    result = []
    for e in entries:
        result.append({
            "url": e.url,
            "method": e.method,
            "status": e.status,
            "resource_type": e.resource_type,
            "request_headers": e.request_headers,
            "response_headers": e.response_headers,
            "request_body": e.request_body,
            "response_body": e.response_body[:500] if e.response_body else None,
        })

    return json.dumps(result, indent=2)


@mcp.tool()
async def clear_network_log() -> str:
    """Clear the captured network log."""
    session.network_log.clear()
    return "Network log cleared."


@mcp.tool()
async def set_network_capture(enabled: bool = True, capture_bodies: bool = False) -> str:
    """
    Configure network capture settings.

    Args:
        enabled: Enable or disable network capture
        capture_bodies: Also capture request/response bodies (can be large!)

    Returns:
        Confirmation
    """
    session.capture_network = enabled
    session.capture_bodies = capture_bodies
    return f"Network capture: {'enabled' if enabled else 'disabled'}, bodies: {'captured' if capture_bodies else 'not captured'}"


@mcp.tool()
async def wait_for_request(url_pattern: str, timeout: int = 30000) -> str:
    """
    Wait for a network request matching a URL pattern.

    Args:
        url_pattern: URL substring or pattern to match
        timeout: Maximum wait time in milliseconds

    Returns:
        Request details when matched
    """
    if not session.page:
        return "Error: No active page."

    try:
        async with session.page.expect_request(
            lambda req: url_pattern in req.url,
            timeout=timeout
        ) as request_info:
            request = await request_info.value
            return json.dumps({
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "post_data": request.post_data,
            }, indent=2)
    except Exception as e:
        return f"Error waiting for request: {str(e)}"


@mcp.tool()
async def wait_for_response(url_pattern: str, timeout: int = 30000) -> str:
    """
    Wait for a network response matching a URL pattern.

    Args:
        url_pattern: URL substring or pattern to match
        timeout: Maximum wait time in milliseconds

    Returns:
        Response details when matched
    """
    if not session.page:
        return "Error: No active page."

    try:
        async with session.page.expect_response(
            lambda resp: url_pattern in resp.url,
            timeout=timeout
        ) as response_info:
            response = await response_info.value
            try:
                body = await response.text()
            except Exception:
                body = None
            return json.dumps({
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers),
                "body": body[:2000] if body else None,
            }, indent=2)
    except Exception as e:
        return f"Error waiting for response: {str(e)}"


# ============================================================================
# JavaScript Evaluation Tools
# ============================================================================

@mcp.tool()
async def evaluate(expression: str) -> str:
    """
    Execute JavaScript in the page context.

    Args:
        expression: JavaScript expression or function to evaluate

    Returns:
        JSON-serialized result
    """
    if not session.page:
        return "Error: No active page."

    try:
        result = await session.page.evaluate(expression)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error evaluating JS: {str(e)}"


@mcp.tool()
async def evaluate_on_element(selector: str, expression: str) -> str:
    """
    Execute JavaScript on a specific element.

    Args:
        selector: CSS selector for the element
        expression: JavaScript function receiving the element (e.g., "el => el.value")

    Returns:
        JSON-serialized result
    """
    if not session.page:
        return "Error: No active page."

    try:
        result = await session.page.locator(selector).evaluate(expression)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error evaluating on element: {str(e)}"


# ============================================================================
# Wait & Timing Tools
# ============================================================================

@mcp.tool()
async def wait_for_selector(
    selector: str,
    state: str = "visible",
    timeout: int = 30000,
) -> str:
    """
    Wait for an element to reach a specific state.

    Args:
        selector: CSS selector to wait for
        state: Target state - "attached", "detached", "visible", or "hidden"
        timeout: Maximum wait time in milliseconds

    Returns:
        Success or timeout message
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.wait_for_selector(selector, state=state, timeout=timeout)
        return f"Element '{selector}' is now {state}."
    except Exception as e:
        return f"Timeout waiting for '{selector}': {str(e)}"


@mcp.tool()
async def wait_for_load_state(state: str = "load") -> str:
    """
    Wait for the page to reach a load state.

    Args:
        state: Load state - "load", "domcontentloaded", or "networkidle"

    Returns:
        Confirmation
    """
    if not session.page:
        return "Error: No active page."

    await session.page.wait_for_load_state(state)
    return f"Page reached '{state}' state."


@mcp.tool()
async def wait(milliseconds: int) -> str:
    """
    Wait for a specified duration.

    Args:
        milliseconds: Time to wait in milliseconds

    Returns:
        Confirmation
    """
    await asyncio.sleep(milliseconds / 1000)
    return f"Waited {milliseconds}ms."


# ============================================================================
# Cookie & Storage Tools
# ============================================================================

@mcp.tool()
async def get_cookies(url: str | None = None) -> str:
    """
    Get cookies from the browser context.

    Args:
        url: Optional URL to filter cookies for

    Returns:
        JSON array of cookies
    """
    if not session.page:
        return "Error: No active page."

    try:
        context = session.page.context
        if url:
            cookies = await context.cookies(url)
        else:
            cookies = await context.cookies()
        return json.dumps(cookies, indent=2)
    except Exception as e:
        return f"Error getting cookies: {str(e)}"


@mcp.tool()
async def set_cookie(
    name: str,
    value: str,
    url: str | None = None,
    domain: str | None = None,
    path: str = "/",
    expires: int | None = None,
    http_only: bool = False,
    secure: bool = False,
) -> str:
    """
    Set a cookie in the browser context.

    Args:
        name: Cookie name
        value: Cookie value
        url: URL to associate with the cookie
        domain: Cookie domain
        path: Cookie path
        expires: Expiration timestamp (Unix epoch)
        http_only: HTTP-only flag
        secure: Secure flag

    Returns:
        Confirmation
    """
    if not session.page:
        return "Error: No active page."

    cookie = {
        "name": name,
        "value": value,
        "path": path,
        "httpOnly": http_only,
        "secure": secure,
    }
    if url:
        cookie["url"] = url
    if domain:
        cookie["domain"] = domain
    if expires:
        cookie["expires"] = expires

    try:
        await session.page.context.add_cookies([cookie])
        return f"Cookie '{name}' set."
    except Exception as e:
        return f"Error setting cookie: {str(e)}"


@mcp.tool()
async def clear_cookies() -> str:
    """Clear all cookies from the browser context."""
    if not session.page:
        return "Error: No active page."

    await session.page.context.clear_cookies()
    return "All cookies cleared."


@mcp.tool()
async def get_local_storage() -> str:
    """Get all localStorage data from the current page."""
    if not session.page:
        return "Error: No active page."

    try:
        data = await session.page.evaluate("() => Object.entries(localStorage)")
        return json.dumps(dict(data), indent=2)
    except Exception as e:
        return f"Error getting localStorage: {str(e)}"


@mcp.tool()
async def set_local_storage(key: str, value: str) -> str:
    """
    Set a localStorage item.

    Args:
        key: Storage key
        value: Storage value

    Returns:
        Confirmation
    """
    if not session.page:
        return "Error: No active page."

    try:
        await session.page.evaluate(f"localStorage.setItem({json.dumps(key)}, {json.dumps(value)})")
        return f"localStorage['{key}'] set."
    except Exception as e:
        return f"Error setting localStorage: {str(e)}"


# ============================================================================
# Dialog & Alert Handling
# ============================================================================

@mcp.tool()
async def handle_dialog(action: str = "accept", prompt_text: str | None = None) -> str:
    """
    Set up automatic handling for dialogs (alert, confirm, prompt).

    Args:
        action: How to handle dialogs - "accept" or "dismiss"
        prompt_text: Text to enter for prompt dialogs

    Returns:
        Confirmation
    """
    if not session.page:
        return "Error: No active page."

    async def dialog_handler(dialog):
        if action == "accept":
            if prompt_text and dialog.type == "prompt":
                await dialog.accept(prompt_text)
            else:
                await dialog.accept()
        else:
            await dialog.dismiss()

    session.page.on("dialog", dialog_handler)
    return f"Dialog handler set: {action}" + (f" with text '{prompt_text}'" if prompt_text else "")


# ============================================================================
# Frame Handling
# ============================================================================

@mcp.tool()
async def list_frames() -> str:
    """List all frames in the current page."""
    if not session.page:
        return "Error: No active page."

    frames = []
    for frame in session.page.frames:
        frames.append({
            "name": frame.name,
            "url": frame.url,
        })
    return json.dumps(frames, indent=2)


@mcp.tool()
async def frame_locator(frame_selector: str, element_selector: str, action: str = "click") -> str:
    """
    Interact with an element inside an iframe.

    Args:
        frame_selector: Selector for the iframe element
        element_selector: Selector for the element inside the frame
        action: Action to perform - "click", "fill", or "get_text"

    Returns:
        Action result
    """
    if not session.page:
        return "Error: No active page."

    try:
        frame = session.page.frame_locator(frame_selector)
        locator = frame.locator(element_selector)

        if action == "click":
            await locator.click()
            return f"Clicked element in frame."
        elif action == "get_text":
            return await locator.inner_text()
        else:
            return f"Unknown action: {action}"
    except Exception as e:
        return f"Error with frame: {str(e)}"


# ============================================================================
# Debug & Inspection Tools
# ============================================================================

@mcp.tool()
async def get_browser_info() -> str:
    """Get information about the current browser session."""
    if not session.browser:
        return json.dumps({"status": "No browser running"})

    info = {
        "status": "running",
        "pages": list(session.pages.keys()),
        "active_page": None,
        "network_capture": session.capture_network,
        "capture_bodies": session.capture_bodies,
        "network_log_size": len(session.network_log),
    }

    if session.page:
        info["active_page"] = session.page.url

    return json.dumps(info, indent=2)


@mcp.tool()
async def inspect_element(selector: str) -> str:
    """
    Get detailed information about an element.

    Args:
        selector: CSS selector for the element

    Returns:
        JSON object with element details
    """
    if not session.page:
        return "Error: No active page."

    try:
        locator = session.page.locator(selector)

        info = await locator.evaluate("""el => ({
            tagName: el.tagName,
            id: el.id,
            className: el.className,
            name: el.name,
            type: el.type,
            value: el.value,
            href: el.href,
            src: el.src,
            innerText: el.innerText?.substring(0, 200),
            innerHTML: el.innerHTML?.substring(0, 500),
            isVisible: el.offsetParent !== null,
            rect: el.getBoundingClientRect(),
            attributes: Array.from(el.attributes || []).map(a => ({name: a.name, value: a.value})),
        })""")

        return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error inspecting element: {str(e)}"


@mcp.tool()
async def get_console_logs() -> str:
    """
    Get console logs from the page.
    Note: This starts capturing from the point it's called.

    Returns:
        Instructions for console log capture
    """
    if not session.page:
        return "Error: No active page."

    logs = []

    def handle_console(msg):
        logs.append({
            "type": msg.type,
            "text": msg.text,
        })

    session.page.on("console", handle_console)
    return "Console log capture started. Reload the page or trigger actions to capture logs."


def main():
    """Run the Camoufox MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
