FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pinned Pixi binary with checksum verification.
COPY scripts/install_pixi.sh /tmp/install_pixi.sh
RUN chmod +x /tmp/install_pixi.sh && /tmp/install_pixi.sh /root/.pixi/bin && rm -f /tmp/install_pixi.sh
ENV PATH="/root/.pixi/bin:${PATH}"

# Copy application code
COPY . .

# Install dependencies from pixi.toml + pixi.lock
RUN pixi install --locked

# Start scripts must be executable in Docker runtime.
RUN chmod +x /app/scripts/start_api.sh /app/scripts/start_worker.sh

EXPOSE 8000

# Default command keeps container startup deterministic and avoids the dev reloader.
CMD ["/app/scripts/start_api.sh"]
