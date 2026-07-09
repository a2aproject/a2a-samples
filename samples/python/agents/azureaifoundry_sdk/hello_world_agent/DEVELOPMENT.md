# Development Guide

This guide covers development, testing, and deployment of the Hello World Azure AI Foundry Agent.

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- Azure AI Foundry project with deployed model
- Azure CLI (for authentication)

### Local Development

1. **Clone and setup**:
   ```bash
   cd hello_world_agent
   uv sync  # or pip install -e .
   cp .env.template .env
   # Edit .env with your credentials
   ```

2. **Run in development mode**:
   ```bash
   python cli.py web --reload
   ```

3. **Access the application**:
   - Web UI: http://localhost:8000
   - Health check: http://localhost:8000/health

## 🧪 Testing

### Unit Tests

```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=hello_world_agent

# Run specific test
python -m pytest tests/test_hello_agent.py::TestHelloWorldAgent::test_init
```

### Integration Tests

```bash
# Check environment
python cli.py check --verbose

# Test console interaction
python cli.py console

# Test examples
python examples/simple_chat.py
python examples/multi_turn.py
python examples/error_handling.py
```

### Manual Testing

1. **Web Interface**:
   - Open browser to http://localhost:8000
   - Test real-time messaging
   - Test error scenarios (disconnect/reconnect)
   - Test mobile responsiveness

2. **API Endpoints**:
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Create session
   curl -X POST http://localhost:8000/api/session
   
   # Send message
   curl -X POST http://localhost:8000/api/message \
     -H "Content-Type: application/json" \
     -d '{"session_id": "your-session-id", "message": "Hello!"}'
   ```

## 🐳 Docker Development

### Build and Run

```bash
# Build image
docker build -t hello-world-agent .

# Run container
docker run -p 8000:8000 \
  -e AZURE_AI_FOUNDRY_PROJECT_ENDPOINT="your-endpoint" \
  -e AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME="your-model" \
  hello-world-agent

# Using Docker Compose
docker-compose up --build
```

### Docker Development Workflow

```bash
# Development with auto-reload
docker-compose -f docker-compose.dev.yml up

# Production build
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📁 Project Structure Explained

```
hello_world_agent/
├── __main__.py           # Application entry point
├── web_app.py           # Starlette web application
├── hello_agent.py       # Core Azure AI agent logic
├── cli.py              # Command-line interface
├── utils.py            # Utility functions
├── client.py           # Test client
├── templates/          # Jinja2 templates
│   └── index.html      # Main chat interface
├── static/             # Static assets
│   └── style.css       # Additional styles
├── examples/           # Usage examples
├── tests/             # Test suite
└── docs/              # Documentation
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT` | Yes | Azure AI project endpoint | `https://your-project.cognitiveservices.azure.com/` |
| `AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME` | Yes | Model deployment name | `gpt-4` |
| `AZURE_CLIENT_ID` | No | Service principal client ID | `your-client-id` |
| `AZURE_CLIENT_SECRET` | No | Service principal secret | `your-secret` |
| `AZURE_TENANT_ID` | No | Azure tenant ID | `your-tenant-id` |

### Configuration Files

- `.env` - Local environment variables
- `pyproject.toml` - Python project configuration
- `docker-compose.yml` - Docker services configuration

## 🚀 Deployment

### Local Production

```bash
# Install production dependencies
uv sync --no-dev

# Run with production server
python cli.py web --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build production image
docker build -t hello-world-agent:prod .

# Run production container
docker run -d \
  --name hello-world-agent \
  -p 8000:8000 \
  --restart unless-stopped \
  -e AZURE_AI_FOUNDRY_PROJECT_ENDPOINT="your-endpoint" \
  -e AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME="your-model" \
  hello-world-agent:prod
```

### Cloud Deployment

#### Azure Container Instances

```bash
# Create resource group
az group create --name hello-world-rg --location eastus

# Deploy container
az container create \
  --resource-group hello-world-rg \
  --name hello-world-agent \
  --image hello-world-agent:prod \
  --dns-name-label hello-world-agent-unique \
  --ports 8000 \
  --environment-variables \
    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT="your-endpoint" \
    AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME="your-model"
```

#### Azure App Service

```bash
# Create app service plan
az appservice plan create \
  --name hello-world-plan \
  --resource-group hello-world-rg \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --resource-group hello-world-rg \
  --plan hello-world-plan \
  --name hello-world-agent-app \
  --deployment-container-image-name hello-world-agent:prod
```

## 🐛 Debugging

### Common Issues

1. **Authentication Errors**:
   ```bash
   # Check Azure CLI login
   az account show
   
   # Login if needed
   az login
   ```

2. **Module Import Errors**:
   ```bash
   # Ensure proper installation
   pip install -e .
   
   # Check Python path
   python -c "import sys; print(sys.path)"
   ```

3. **Port Already in Use**:
   ```bash
   # Find process using port
   lsof -i :8000
   
   # Kill process
   kill -9 <PID>
   
   # Or use different port
   python cli.py web --port 3000
   ```

### Debug Mode

```bash
# Enable debug logging
export AZURE_LOG_LEVEL=DEBUG

# Run with verbose output
python cli.py web --reload

# Check health endpoint
curl http://localhost:8000/health | jq
```

## 📊 Monitoring

### Health Checks

- **Application**: `GET /health`
- **Docker**: Built-in healthcheck
- **Kubernetes**: Readiness/liveness probes

### Logging

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# Check logs in Docker
docker logs hello-world-agent
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Make changes and test**: `python -m pytest`
4. **Commit changes**: `git commit -m "Add new feature"`
5. **Push to branch**: `git push origin feature/new-feature`
6. **Create pull request**

### Code Style

```bash
# Format code
black hello_world_agent/
isort hello_world_agent/

# Type checking
mypy hello_world_agent/

# Linting
flake8 hello_world_agent/
```
