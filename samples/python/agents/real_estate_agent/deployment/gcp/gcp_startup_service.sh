#!/bin/bash
set -e

# Wait for the Docker daemon to be ready.
while ! docker info > /dev/null 2>&1; do
    echo "Waiting for Docker to start..."
    sleep 2
done

# Define absolute paths for all critical files.
BASE_PATH="/home/app-runner/agent"
COMPOSE_FILE="${BASE_PATH}/docker-compose.yml"
ENV_FILE="${BASE_PATH}/.env"

# Start dependency services first.
/usr/local/bin/docker-compose --project-directory ${BASE_PATH} --env-file ${ENV_FILE} -f ${COMPOSE_FILE} up --build -d dafty-mcp ollama ollama-setup

# The ngrok service is managed by systemd and is guaranteed to be running
# before this script starts, so we can proceed directly.

# Get the public URL from the ngrok API.
NGROK_URL=""
# Retry for up to 30 seconds to get the ngrok URL
for _ in {1..15}; do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[] | select(.proto=="https") | .public_url')
    if [ -n "$NGROK_URL" ]; then
        break
    fi
    echo "Waiting for ngrok tunnel to be ready..."
    sleep 2
done

if [ -z "$NGROK_URL" ]; then
    echo "Failed to retrieve ngrok URL after multiple attempts. Startup aborted." >&2
    exit 1
fi


# Update the .env file with the public URL idempotently.
if grep -q "^AGENT_PUBLIC_URL=" "${ENV_FILE}"; then
    sed -i "s|^AGENT_PUBLIC_URL=.*|AGENT_PUBLIC_URL=${NGROK_URL}|" "${ENV_FILE}"
else
    echo "AGENT_PUBLIC_URL=${NGROK_URL}" >> "${ENV_FILE}"
fi

# Now, start the real-estate-agent service with the correct environment.
/usr/local/bin/docker-compose --project-directory ${BASE_PATH} --env-file ${ENV_FILE} -f ${COMPOSE_FILE} up -d --build real-estate-agent

echo "Startup script completed. Service is online at ${NGROK_URL}"