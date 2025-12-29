# Camoufox MCP Server

An MCP (Model Context Protocol) server for [Camoufox](https://camoufox.com/) - the anti-detect browser built on Firefox. This server enables Claude to control a stealthy browser for web scraping, form automation, and network analysis.

## Features

- **Browser Control**: Launch, close, and manage multiple browser tabs
- **Anti-Detect**: Built on Camoufox with automatic fingerprint spoofing
- **Network Analysis**: Capture and analyze all HTTP requests/responses
- **Page Interaction**: Click, fill forms, type, select dropdowns, check boxes
- **Content Extraction**: Get text, HTML, attributes from any element
- **JavaScript Execution**: Run custom JS in page context
- **Screenshots**: Capture full page or specific elements
- **Cookie/Storage**: Manage cookies and localStorage
- **Human-like Behavior**: Optional cursor humanization

## Installation

```bash
# Clone and enter directory
cd camoufox-mcp

# Install dependencies with uv
uv sync

# Install Camoufox browser (downloads custom Firefox build)
uv run python -c "from camoufox.sync_api import Camoufox; print('OK')"

# Install Playwright browsers
uv run playwright install firefox
```

## Configuration

Add to your Claude Code settings (`~/.claude/settings.json` or `.claude/settings.json`):

```json
{
  "mcpServers": {
    "camoufox": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/camoufox-mcp", "run", "python", "main.py"]
    }
  }
}
```

Then restart Claude Code.

## Available Tools (49 total)

### Browser Management
| Tool | Description |
|------|-------------|
| `launch_browser` | Launch Camoufox with anti-detect options (headless, proxy, OS spoof, humanize) |
| `close_browser` | Close browser and cleanup resources |
| `new_page` | Create a new browser tab |
| `switch_page` | Switch between tabs |
| `list_pages` | List all open tabs with URLs |
| `get_browser_info` | Get browser session status |

### Navigation
| Tool | Description |
|------|-------------|
| `goto` | Navigate to a URL |
| `reload` | Reload current page |
| `go_back` | Navigate back in history |
| `go_forward` | Navigate forward in history |
| `get_url` | Get current page URL |
| `get_page_title` | Get page title |

### Page Interaction
| Tool | Description |
|------|-------------|
| `click` | Click an element (supports CSS, XPath) |
| `fill` | Fill input/textarea with value |
| `type_text` | Type text character by character (human-like) |
| `press_key` | Press keyboard key (Enter, Tab, etc.) |
| `select_option` | Select dropdown option by value/label/index |
| `check` | Check a checkbox or radio button |
| `uncheck` | Uncheck a checkbox |
| `hover` | Hover over an element |
| `scroll` | Scroll page or element into view |
| `upload_file` | Upload file to file input |

### Content Extraction
| Tool | Description |
|------|-------------|
| `get_text` | Get text content from element or page |
| `get_html` | Get HTML (inner or outer) |
| `get_attribute` | Get element attribute value |
| `query_selector_all` | Query multiple elements, extract data |
| `inspect_element` | Get detailed element info (tag, rect, attributes) |

### Network Analysis
| Tool | Description |
|------|-------------|
| `get_network_log` | Get captured requests with filtering |
| `clear_network_log` | Clear captured network log |
| `set_network_capture` | Enable/disable capture, include bodies |
| `wait_for_request` | Wait for specific request pattern |
| `wait_for_response` | Wait for specific response pattern |

### Screenshots & Viewport
| Tool | Description |
|------|-------------|
| `screenshot` | Take screenshot (full page, element, or viewport) |
| `get_viewport_size` | Get current viewport dimensions |
| `set_viewport_size` | Set viewport dimensions |

### JavaScript
| Tool | Description |
|------|-------------|
| `evaluate` | Execute JavaScript in page context |
| `evaluate_on_element` | Execute JS on specific element |

### Waiting
| Tool | Description |
|------|-------------|
| `wait_for_selector` | Wait for element state (visible, hidden, etc.) |
| `wait_for_load_state` | Wait for page load state |
| `wait` | Wait for specified milliseconds |

### Cookies & Storage
| Tool | Description |
|------|-------------|
| `get_cookies` | Get all cookies |
| `set_cookie` | Set a cookie |
| `clear_cookies` | Clear all cookies |
| `get_local_storage` | Get localStorage data |
| `set_local_storage` | Set localStorage item |

### Frames & Dialogs
| Tool | Description |
|------|-------------|
| `list_frames` | List all frames in page |
| `frame_locator` | Interact with elements inside iframes |
| `handle_dialog` | Set up dialog (alert/confirm/prompt) handler |
| `get_console_logs` | Capture console logs |

## Usage Examples

### Basic Web Scraping

```
User: Launch a browser and go to example.com, then get the page title

Claude: [Uses launch_browser, goto, get_page_title]
```

### Form Automation

```
User: Fill out the login form with username "test" and password "secret", then submit

Claude: [Uses fill for username, fill for password, click on submit button]
```

### Network Analysis

```
User: Go to the website and show me all API calls it makes

Claude: [Uses set_network_capture, goto, get_network_log with filtering]
```

### Debug Session

```
User: Take a screenshot and inspect the submit button element

Claude: [Uses screenshot, inspect_element]
```

## Running Tests

```bash
# Run all tests
uv run pytest test_server.py -v

# Run specific test class
uv run pytest test_server.py::TestNavigation -v

# Run with short traceback
uv run pytest test_server.py -v --tb=short
```

## Development

```bash
# Run server directly (for debugging)
uv run python main.py

# Check available tools
uv run python -c "from main import mcp; print([t.name for t in mcp._tool_manager._tools.values()])"
```

## Architecture

- `main.py` - MCP server with all 49 tools
- `test_server.py` - Comprehensive test suite
- Uses [FastMCP](https://github.com/modelcontextprotocol/python-sdk) for MCP protocol
- Uses [Camoufox](https://github.com/daijro/camoufox) for anti-detect browser
- Uses [Playwright](https://playwright.dev/) for browser automation

## License

MIT

## Credits

- [Camoufox](https://github.com/daijro/camoufox) - Anti-detect Firefox browser
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Model Context Protocol
- [Playwright](https://playwright.dev/) - Browser automation
