# Camoufox MCP Server - Docker Image
# Multi-stage build for optimized image size

# ============================================================================
# Stage 1: Build environment
# ============================================================================
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# ============================================================================
# Stage 2: Runtime environment
# ============================================================================
FROM python:3.12-slim AS runtime

# Install runtime dependencies for Firefox/Camoufox
RUN apt-get update && apt-get install -y --no-install-recommends \
    # X11 and virtual framebuffer
    xvfb \
    x11vnc \
    # Firefox dependencies
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    # Fonts
    fonts-liberation \
    fonts-noto-color-emoji \
    # Utilities
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user
RUN useradd -m -s /bin/bash camoufox

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY main.py ./
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install the project
RUN uv sync --frozen --no-dev

# Create directories for outputs
RUN mkdir -p /app/screenshots /app/downloads && \
    chown -R camoufox:camoufox /app

# Download Camoufox browser and Playwright browsers
RUN /app/.venv/bin/python -c "from camoufox.sync_api import Camoufox; print('Camoufox OK')" && \
    /app/.venv/bin/playwright install firefox && \
    chown -R camoufox:camoufox /root/.cache 2>/dev/null || true

# Environment variables
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Create X11 socket directory (needed for Xvfb as non-root)
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

# Copy entrypoint script and make executable
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/

# Switch to non-root user
USER camoufox

# Expose VNC port (optional, for debugging)
EXPOSE 5900

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -x "Xvfb" > /dev/null || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "main.py"]
