FROM python:3.12-slim
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Change the working directory to the `app` directory
WORKDIR /app
COPY . /app
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync --frozen

EXPOSE $PORT

CMD ["uv", "run", "cocktail_server.py"]
