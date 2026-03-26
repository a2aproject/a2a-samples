# Use the official Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Node.js for MCP
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Notion MCP server globally
RUN npm install -g @notionhq/notion-mcp-server@1.9.1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with uv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0

# Expose the port Cloud Run will use
EXPOSE 8080

# Run the A2A server
CMD ["python", "agent.py"]
