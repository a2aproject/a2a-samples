#!/bin/bash
set -e

# Install Docker first to ensure the 'docker' group exists.
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Create a dedicated user for the application if it doesn't already exist.
id -u app-runner &>/dev/null || sudo useradd -m -s /bin/bash app-runner
sudo usermod -aG docker app-runner

# Create the application directory.
sudo mkdir -p /home/app-runner/agent
sudo chown -R app-runner:app-runner /home/app-runner/agent

# Install ngrok and jq.
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt-get update
sudo apt-get install -y ngrok jq

# Install Docker Compose v2.
LATEST_COMPOSE_VERSION="v2.27.0" # Or another specific, tested version
COMPOSE_PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
sudo curl -L "https://github.com/docker/compose/releases/download/${LATEST_COMPOSE_VERSION}/docker-compose-${COMPOSE_PLATFORM}" -o /usr/local/bin/docker-compose

# Verify the binary's checksum for security
sudo curl -sL "https://github.com/docker/compose/releases/download/${LATEST_COMPOSE_VERSION}/docker-compose-${COMPOSE_PLATFORM}.sha256" -o /tmp/docker-compose.sha256
(cd /tmp && echo "$(cat docker-compose.sha256)  /usr/local/bin/docker-compose" | sha256sum --check --strict)
if [ $? -ne 0 ]; then
    echo "Docker Compose checksum validation failed. Aborting." >&2
    exit 1
fi
rm /tmp/docker-compose.sha256

sudo chmod +x /usr/local/bin/docker-compose

# Configure ngrok authtoken for the app-runner user.
echo "Please enter your ngrok authtoken:"
read -s NGROK_AUTHTOKEN
if [ -z "$NGROK_AUTHTOKEN" ]; then
    echo "ngrok authtoken cannot be empty."
    exit 1
fi
sudo -u app-runner ngrok config add-authtoken "$NGROK_AUTHTOKEN"

# Create systemd service for ngrok.
sudo bash -c 'cat > /etc/systemd/system/ngrok.service <<EOF
[Unit]
Description=ngrok tunnel
After=network.target

[Service]
User=app-runner
ExecStart=ngrok http 3001
Restart=always

[Install]
WantedBy=multi-user.target
EOF'
sudo systemctl enable ngrok.service

# Create systemd service for the main application startup.
sudo bash -c 'cat > /etc/systemd/system/startup.service <<EOF
[Unit]
Description=Run startup script
After=network.target docker.service
Requires=ngrok.service

[Service]
User=app-runner
Type=oneshot
WorkingDirectory=/home/app-runner/agent
ExecStart=/opt/startup.sh

[Install]
WantedBy=multi-user.target
EOF'
sudo systemctl enable startup.service

echo "Full setup complete. Please copy application files and reboot."