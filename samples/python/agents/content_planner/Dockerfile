FROM python:3.13-slim-trixie

RUN apt-get update && apt-get install -y curl git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /bin/

ENV UV_LINK_MODE=copy \
    PRODUCTION_MODE=true

COPY samples/python/agents/content_planner/ /app
WORKDIR /app

RUN uv sync --no-cache --locked --link-mode copy

ENV PRODUCTION_MODE=True \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp

# Create a startup script
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'uv run . &' >> /app/start.sh && \
    echo 'npx --yes tomkis/beeai-a2a-proxy start -p 8000 -r GOOGLE_API_KEY &' >> /app/start.sh && \
    echo 'wait' >> /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 8000

CMD ["/bin/bash", "/app/start.sh"]

