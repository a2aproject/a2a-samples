FROM registry.access.redhat.com/ubi8/python-312

# Set work directory
WORKDIR /opt/app-root/

# Copy Python Project Files (Container context must be the `python` directory)
COPY . /opt/app-root

USER root

# Install system build dependencies and UV package manager
RUN dnf -y update && dnf install -y gcc gcc-c++ \
 && pip install uv

# Set environment variables for uv:
# UV_COMPILE_BYTECODE=1: Compiles Python files to .pyc for faster startup
# UV_LINK_MODE=copy: Ensures files are copied, not symlinked, which can avoid issues
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies using uv sync.
# --frozen: Ensures uv respects the uv.lock file
# --no-install-project: Prevents installing the project itself in this stage
# --no-dev: Excludes development dependencies
# --mount=type=cache: Leverages Docker's build cache for uv, speeding up repeated builds
RUN --mount=type=cache,target=/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the project
RUN --mount=type=cache,target=/.cache/uv \
    uv sync --frozen --no-dev

# Allow non-root user to access the everything in app-root
RUN chgrp -R root /opt/app-root/ && chmod -R g+rwx /opt/app-root/

# Expose default port (change if needed)
EXPOSE 9999

USER 1001

# Run the agent
CMD uv run . --host 0.0.0.0