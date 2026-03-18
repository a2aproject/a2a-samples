# Use the official uv image with Python 3.12
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the shell to bash and enable pipefail for safer pipes
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u14 \
    xz-utils=5.4.1-1 \
    ca-certificates=20230311+deb12u1 \
    procps=2:4.0.2-3 \
    psmisc=23.6-1 \
    git=1:2.39.5-0+deb12u3 \
    && rm -rf /var/lib/apt/lists/*

# Install Go 1.24.13
ENV GO_VERSION=1.24.13
RUN curl -L https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz | tar -C /usr/local -xz
ENV PATH=$PATH:/usr/local/go/bin

# Install Node.js v20.11.1
ENV NODE_VERSION=v20.11.1
RUN curl -L https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz | tar -xJ -C /usr/local --strip-components=1

# Set the working directory
WORKDIR /app

# We assume the user runs docker build -t itk_service -f Dockerfile .
# inside the itk/ directory.
COPY . /app

# Install Python dependencies using uv (JIT during run)
ENV PYTHONPATH=/app
ENV UV_INDEX_URL=https://pypi.org/simple

# Go and Node binaries are installed globally for JIT use

# Expose the service port
EXPOSE 8000

# Set environment variables if needed
ENV PYTHONUNBUFFERED=1

# Command to run the service
CMD ["uv", "run", "itk_service.py"]
