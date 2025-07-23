# Tracing with A2A SDK

This sample project demonstrates the distributed tracing feature in A2A SDK, with traces exported to Jaeger. It features an agent built with  Google's Agent Development Kit (ADK), utilizing the Google Search tool to respond to user queries.

The primary goal is to showcase how to enable and export traces from an A2A server and client, and how these traces can be collected and visualized using Jaeger and Grafana.

## Core Functionality

* **Agent:** A simple conversational agent that uses Google Search to answer questions.
* **Tracing:** Enabled based on the configuration in  `__main__.py`.
* **Trace Export:** Traces are sent to a Jaeger backend running in Docker.
* **Visualization:** Traces can be viewed and analyzed in the Jaeger UI and Grafana.

## Files

* `__main__.py`: The main entry point for the application. It sets up the OpenTelemetry tracer, Jaeger exporter, and starts the A2A Server.
* `agent_executor.py`: Contains the logic for the agent, including the integration of the Google Search tool and custom span creation for tracing specific operations.
* `docker-compose.yaml`: A Docker Compose file to easily set up and run Jaeger and Grafana services.

## Prerequisites

* Python 3.10+
* Docker and Docker Compose
* Google API Key

## Setup

1. **Set Environment Variables:**

    ```bash
    export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    ```

    Replace `"YOUR_GOOGLE_API_KEY"` with your api key

2. **Start Jaeger and Grafana:**

    ```bash
    docker compose up -d
    ```

    This will start:
    * **Jaeger:** UI accessible at `http://localhost:16686`.
    * **Grafana:** UI accessible at `http://localhost:3000` (default login: `admin`/`admin`).

    **Important Note on OTLP Port:** The Python application (`__main__.py`) is configured to send traces to Jaeger via OTLP grpc . The provided `docker-compose.yaml` for Jaeger enables the OTLP collector. Ensure that port `4317` is mapped from the host to the Jaeger container. If you wish to change ports in docker-compose.yaml, `__main__.py` has to be updates.

## Running the Application

1. Once the environment variables are set and the Docker containers are running, execute the main script:

    ```bash
    uv run .
    ```

2. The application will start on port 10020
    Run the CLI or the UI tool to interact with the agent. The traces are collected and sent to Jaeger.

3. To stop the application, you can typically use `Ctrl+C`.

## Viewing Traces

### 1. Jaeger UI

* Open your web browser and navigate to the Jaeger UI: `http://localhost:16686`.
* In the "Service" dropdown menu on the left sidebar under search, select `a2a-telemetry-sample` (this is the service name configured in `__main__.py`).
* Click the "Find Traces" button. You should see a list of traces, with each trace corresponding to an interaction with the agent.
* Click on any trace to view its detailed span hierarchy, logs, and tags. You will see spans for the overall agent invocation, calls to the Google Search tool, and LLM (if applicable) processing.

### 2. Grafana UI

Grafana can be configured to use Jaeger as a data source, allowing you to visualize traces and create dashboards.

* **Access Grafana:** Open `http://localhost:3000` in your browser. Log in using the default credentials: username `admin`, password `admin`. You may be prompted to change the password on your first login.

* **Add Jaeger as a Data Source:**
    1. Navigate to "Connections" (or click the gear icon for "Configuration" then "Data Sources" in older Grafana versions).
    2. Click on "Add new connection" or "Add data source".
    3. Search for "Jaeger" in the list of available data sources and select it.
    4. Configure the Jaeger data source settings:
        * **Name:** You can leave it as `Jaeger` or choose a custom name.
        * **URL:** `http://jaeger:16686`
            *(This URL uses the Jaeger service name `jaeger` as defined in `docker-compose.yaml`, allowing Grafana to connect to Jaeger within the Docker network).*
        * Leave other settings as default unless you have specific requirements.
    5. Click "Save & Test". You should see a confirmation message like "Data source is working".

* **Explore Traces in Grafana:**
    1. On the left sidebar, navigate to "Explore".
    2. From the dropdown menu at the top-left of the Explore view, select the Jaeger data source you just configured.
    3. You can now query for traces:
        * Use the "Service" dropdown to select `a2a-telemetry-sample`.
        * Search by Trace ID if you have one, or use other filters.
    4. You can also create dashboards (Dashboard -> New Dashboard -> Add visualization) and use the Jaeger data source to build panels for trace data.

## Stopping the Services

To stop and remove the Jaeger and Grafana containers defined in `docker-compose.yaml`, run:

```bash
docker compose down
```

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
