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
- **Docker Support**: Full containerized deployment with optional VNC debugging

---

## Quick Start (Docker - Recommended)

### Option 1: Docker Compose (Easiest)

```bash
# Clone the repo
git clone <repo-url>
cd camoufox-mcp

# Start the server
docker compose up -d camoufox

# Or with VNC debugging (view browser at http://localhost:6080)
docker compose --profile debug up -d
```

### Option 2: Docker Run

```bash
# Build the image
docker build -t camoufox-mcp .

# Run for MCP
docker run -i --rm camoufox-mcp
```

### Claude Code Configuration (Docker)

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "camoufox": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "camoufox-mcp"]
    }
  }
}
```

Or with Docker Compose:

```json
{
  "mcpServers": {
    "camoufox": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/camoufox-mcp/docker-compose.yml", "run", "--rm", "-T", "camoufox"]
    }
  }
}
```

---

## Installation (Local Development)

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

### Claude Code Configuration (Local)

Add to `~/.claude/settings.json`:

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

---

## Docker Compose Profiles

| Profile | Command | Description |
|---------|---------|-------------|
| Default | `docker compose up camoufox` | MCP server only |
| Debug | `docker compose --profile debug up` | MCP + noVNC web viewer |
| Test | `docker compose --profile test up` | Run test suite |

### VNC Debugging

When using the `debug` profile, you can view the browser live:

1. Start with debug profile: `docker compose --profile debug up`
2. Open http://localhost:6080 in your browser
3. Watch Claude control the browser in real-time!

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
# Enable VNC server (for debugging)
ENABLE_VNC=true

# VNC port (default: 5900)
VNC_PORT=5900

# noVNC web viewer port (default: 6080)
NOVNC_PORT=6080

# Screenshot settings
CAMOUFOX_SCREENSHOT_DIR=/tmp/camoufox_screenshots  # Directory for auto-saved screenshots
CAMOUFOX_SCREENSHOT_AUTO_SAVE=true                  # Always save to file (no base64)
```

### Volumes

The Docker setup persists:
- `./data/screenshots/` - Saved screenshots
- `./data/downloads/` - Downloaded files
- `camoufox-cache` - Browser cache (for faster startups)

---

## Available Tools (55 total)

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

### Compound Actions (Token-Efficient)
| Tool | Description |
|------|-------------|
| `batch_actions` | Execute multiple actions in one call (click, fill, type, press, select, etc.) |
| `fill_form` | Fill multiple form fields at once with optional submit |
| `click_text` | Click element by text content (no selector needed) |
| `click_role` | Click element by ARIA role (button, link, etc.) |
| `fill_by_label` | Fill input by its label text (no selector needed) |
| `fill_placeholder` | Fill input by placeholder text (no selector needed) |

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
| `screenshot` | Take screenshot (saves to file, returns path - no base64 to save context) |
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

---

## Usage Examples

### Basic Web Scraping

```
User: Launch a browser and go to example.com, then get the page title

Claude: [Uses launch_browser, goto, get_page_title]
```

### Form Automation (Token-Efficient)

```
User: Fill out the login form with username "test" and password "secret", then submit

Claude: [Uses fill_form with {"#username": "test", "#password": "secret"} and submit_selector]
# OR uses fill_by_label for "Username" and "Password" fields
# OR uses batch_actions with multiple fill + click actions
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

---

## Running Tests

### Local
```bash
uv run pytest test_server.py -v --tb=short
```

### Docker
```bash
docker compose --profile test run --rm test
```

---

## Development

```bash
# Run server directly (for debugging)
uv run python main.py

# Check available tools
uv run python -c "from main import mcp; print([t.name for t in mcp._tool_manager._tools.values()])"

# Build Docker image
docker build -t camoufox-mcp .

# Run with VNC for debugging
ENABLE_VNC=true docker compose --profile debug up
```

---

## Architecture

```
camoufox-mcp/
├── main.py              # MCP server with 49 tools
├── test_server.py       # Comprehensive test suite (16 tests)
├── Dockerfile           # Multi-stage Docker build
├── docker-compose.yml   # Compose config with profiles
├── docker-entrypoint.sh # Xvfb + VNC startup script
├── pyproject.toml       # Python dependencies
└── README.md            # This file
```

### Technologies
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk) - MCP protocol implementation
- [Camoufox](https://github.com/daijro/camoufox) - Anti-detect Firefox browser
- [Playwright](https://playwright.dev/) - Browser automation
- [Docker](https://www.docker.com/) - Containerization
- [noVNC](https://novnc.com/) - Web-based VNC viewer

---

## Troubleshooting

### Browser not launching in Docker
Ensure Xvfb is running. Check logs:
```bash
docker compose logs camoufox
```

### VNC not connecting
1. Ensure `ENABLE_VNC=true` is set
2. Check port 5900 is not in use
3. For noVNC, check port 6080

### MCP connection issues
1. Verify Docker is running
2. Check the command in Claude settings uses `-i` flag
3. Try running manually: `docker run -i --rm camoufox-mcp`

---

## License

MIT

## Credits

- [Camoufox](https://github.com/daijro/camoufox) - Anti-detect Firefox browser
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Model Context Protocol
- [Playwright](https://playwright.dev/) - Browser automation
- [noVNC](https://novnc.com/) - HTML5 VNC client
