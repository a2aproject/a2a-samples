FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/

EXPOSE 8080
WORKDIR /app

COPY . ./

RUN uv sync

ENTRYPOINT ["uv", "run", ".", "--host", "0.0.0.0", "--port", "8080"]
