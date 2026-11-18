FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY bridge/ bridge/
COPY cli/ cli/
RUN pip install --no-cache-dir .

COPY agents.json ./
ENV AGENTS_CONFIG=/app/agents.json

EXPOSE 8080
CMD ["python", "-m", "bridge"]
