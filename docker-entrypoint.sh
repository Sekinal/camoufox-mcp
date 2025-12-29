#!/bin/bash
set -e

# Start Xvfb (virtual framebuffer) for headless browser
echo "Starting Xvfb on display :99..."
Xvfb :99 -screen 0 1920x1080x24 -ac &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 1

# Optionally start VNC server for debugging
if [ "${ENABLE_VNC:-false}" = "true" ]; then
    echo "Starting VNC server on port 5900..."
    x11vnc -display :99 -forever -shared -rfbport 5900 -nopw &
    echo "VNC server started. Connect to localhost:5900 to view browser."
fi

# Export display
export DISPLAY=:99

# Handle shutdown gracefully
cleanup() {
    echo "Shutting down..."
    kill $XVFB_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Execute the main command
echo "Starting Camoufox MCP server..."
exec "$@"
