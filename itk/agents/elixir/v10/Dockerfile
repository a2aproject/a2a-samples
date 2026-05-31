FROM elixir:1.17-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy mix files first for dependency caching
COPY mix.exs mix.lock ./
RUN mix local.hex --force && mix local.rebar --force
RUN mix deps.get && mix deps.compile

# Copy source
COPY lib/ lib/
RUN mix compile

# Default ports (override with env vars)
ENV ITK_HTTP_PORT=10200
ENV ITK_GRPC_PORT=11200

EXPOSE ${ITK_HTTP_PORT}

CMD ["mix", "run", "--no-halt"]
