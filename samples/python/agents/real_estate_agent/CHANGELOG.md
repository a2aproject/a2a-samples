# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-07-06

### Added
- Deployment scripts for Google Cloud Platform.
- `ngrok` integration for creating a public URL for the agent.
- `gcp_setup.sh` to set up the environment on a GCP VM.
- `gcp_initial_vm_setup.sh` and `gcp_startup_service.sh` for service configuration.

### Changed
- Updated `docker-compose.yml` to use a dedicated network and handle environment variables for deployment.
- The application now listens on `::` to accept connections from any IP address.
- `agent_card.py` now uses an environment variable for the agent's public URL.
- Updated `README.md` with deployment instructions for GCP.

## [0.1.1] - 2025-07-05

### Added
- Integrated `ollama` with the `tinydolphin` model to parse natural language queries into structured JSON.
- A new `parse_query` tool in the `dafty-mcp` to handle query parsing.

### Changed
- The `agent_executor` now calls the `parse_query` tool before searching for properties.
- The `dafty-mcp` client now has a generic `call_tool` method.
- Updated `docker-compose.yml` to include the `ollama` and `ollama-setup` services.