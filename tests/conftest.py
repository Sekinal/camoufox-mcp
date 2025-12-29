"""
Shared test fixtures for Camoufox MCP Server tests.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest

# Set test environment variables before importing modules
os.environ["CAMOUFOX_LOG_LEVEL"] = "WARNING"
os.environ["CAMOUFOX_LOG_FORMAT"] = "console"
os.environ["CAMOUFOX_HEADLESS"] = "true"

from src.camoufox_mcp.config import ServerConfig, reset_config
from src.camoufox_mcp.metrics import reset_metrics
from src.camoufox_mcp.session import BrowserSession, reset_session


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def config() -> ServerConfig:
    """Get a fresh configuration for each test."""
    reset_config()
    return ServerConfig.from_env()


@pytest.fixture
async def browser_session() -> AsyncGenerator[BrowserSession, None]:
    """
    Provide a browser session for tests.

    Automatically cleans up after the test.
    """
    reset_session()
    session = BrowserSession()

    yield session

    # Cleanup
    if session.is_running:
        await session.close()


@pytest.fixture
async def launched_browser(browser_session: BrowserSession) -> AsyncGenerator[BrowserSession, None]:
    """
    Provide a launched browser session.

    Use this when you need a browser ready to navigate.
    """
    await browser_session.launch(headless=True)
    yield browser_session


@pytest.fixture
def test_html_file() -> Generator[str, None, None]:
    """
    Create a temporary HTML file for testing interactions.

    Provides a form with various input types for testing.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <style>
            body { font-family: sans-serif; padding: 20px; }
            .hidden { display: none; }
            .container { max-width: 600px; margin: 0 auto; }
            input, select, textarea { margin: 5px 0; padding: 5px; }
            button { padding: 10px 20px; cursor: pointer; }
            #result { margin-top: 20px; padding: 10px; background: #f0f0f0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 id="page-title">Test Form</h1>

            <form id="test-form" data-testid="main-form">
                <div>
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" data-testid="username-input">
                </div>

                <div>
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password">
                </div>

                <div>
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email">
                </div>

                <div>
                    <label for="country">Country:</label>
                    <select id="country" name="country">
                        <option value="">Select...</option>
                        <option value="us">United States</option>
                        <option value="uk">United Kingdom</option>
                        <option value="ca">Canada</option>
                    </select>
                </div>

                <div>
                    <label>
                        <input type="checkbox" id="newsletter" name="newsletter">
                        Subscribe to newsletter
                    </label>
                </div>

                <div>
                    <label>
                        <input type="radio" name="plan" value="free"> Free
                    </label>
                    <label>
                        <input type="radio" name="plan" value="pro"> Pro
                    </label>
                </div>

                <div>
                    <label for="message">Message:</label>
                    <textarea id="message" name="message" rows="4"></textarea>
                </div>

                <div>
                    <label for="file">Upload:</label>
                    <input type="file" id="file" name="file">
                </div>

                <button type="submit" id="submit-btn">Submit</button>
                <button type="button" id="reset-btn">Reset</button>
            </form>

            <div id="result" class="hidden"></div>

            <div id="dynamic-content" style="margin-top: 20px;">
                <button id="load-more" onclick="loadMore()">Load More</button>
                <div id="items"></div>
            </div>

            <iframe id="test-iframe" src="about:blank" style="width: 100%; height: 100px; border: 1px solid #ccc;"></iframe>
        </div>

        <script>
            // Form submission handler
            document.getElementById('test-form').addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                const result = {};
                formData.forEach((value, key) => result[key] = value);
                document.getElementById('result').textContent = JSON.stringify(result, null, 2);
                document.getElementById('result').classList.remove('hidden');
            });

            // Reset button handler
            document.getElementById('reset-btn').addEventListener('click', function() {
                document.getElementById('test-form').reset();
                document.getElementById('result').classList.add('hidden');
            });

            // Dynamic content loader
            let itemCount = 0;
            function loadMore() {
                const container = document.getElementById('items');
                for (let i = 0; i < 5; i++) {
                    itemCount++;
                    const div = document.createElement('div');
                    div.className = 'item';
                    div.textContent = 'Item ' + itemCount;
                    div.setAttribute('data-item-id', itemCount);
                    container.appendChild(div);
                }
            }

            // Console log for testing
            console.log('Test page loaded');
            console.warn('This is a test warning');
        </script>
    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False
    ) as f:
        f.write(html_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def reset_all():
    """Reset all global state before a test."""
    reset_config()
    reset_metrics()
    reset_session()
    yield
    reset_config()
    reset_metrics()
    reset_session()


@pytest.fixture
def temp_screenshot_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for screenshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
