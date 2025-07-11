# ADK Agent

This sample uses the Agent Development Kit (ADK) to create a simple calendar update Agent which communicates using A2A.

## Prerequisites

- Python 3.10 or higher
- [UV](https://docs.astral.sh/uv/)
- Access to an LLM and API Key

## Running the Sample

1. Navigate to the samples directory:

    ```bash
    cd samples/python/agents/adk_cloud_run
    ```

2. Create an environment file with your API key:

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

3. Run an agent:

    ```bash
    uv run .
    ```

## Setup Config Google Cloud Run

### Create Service Account

Cloud run uses service accounts (SA) when running service instances (link). Create a service account specific for the deployed A2A service.

```sh
gcloud iam service-accounts create a2a-service-account \
  --description="service account for a2a cloud run service" \
  --display-name="A2A cloud run service account"
```

### Add IAM access

Below roles allow cloud run service to access secrets and invoke `predict` API on Vertex AI models.

```sh
gcloud projects add-iam-policy-binding "{your-project-id}" \
  --member="serviceAccount:a2a-service-account@{your-project-id}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
  --role="roles/aiplatform.user"
```

If using AlloyDb, then also add below IAM role bindings.

```sh
gcloud projects add-iam-policy-binding "{your-project-id}" \
  --member="serviceAccount:a2a-service-account@{your-project-id}.iam.gserviceaccount.com" \
  --role="roles/alloydb.client" \
  --role="roles/serviceusage.serviceUsageConsumer"
```

### Configure Secrets

All sensitive credentials should be provided to the server using a secure mechanism. Cloud run allows secrets to be provided as environment variables or dynamic volume mounts.
DB user & password secrets can be created in Secret Manager as below:

```sh
gcloud secrets create alloy_db_user --replication-policy="automatic"
# Create a file user.txt with contents of secret value
gcloud secrets versions add alloy_db_user --data-file="user.txt"

gcloud secrets create alloy_db_pass --replication-policy="automatic"
# Create a file pass.txt with contents of secret value
gcloud secrets versions add alloy_db_pass --data-file="pass.txt"
```

## Deploy to Google Cloud Run

The A2A cloud run service can be exposed publicly [link](https://cloud.google.com/run/docs/authenticating/public) or kept internal to just GCP clients.

When deploying a service to cloud-run, it returns a run.app URL to query the running service. If length is short enough, it would be the deterministic URL of the form:

https://[TAG---]SERVICE_NAME-PROJECT_NUMBER.REGION.run.app

Eg: https://sample-a2a-agent-1234.us-central1.run.app

### Service Authentication

#### IAM based Authentication
IAM can be used, if the clients are within GCP [link](https://cloud.google.com/run/docs/authenticating/service-to-service). Agentspace is one such example of an internal client. The clients can use service accounts and they need to be given IAM role: `roles/run.invoker` 

#### Public Access
The A2A server is responsible for handling agent level auth. They need to provide this auth info in their agent card using the securitySchemes and security params.

Use the param `--allow-unauthenticated` while deploying to cloud run, to allow public access.

### With `InMemoryTaskStore`

```sh
gcloud run deploy sample-a2a-agent \
    --port=8080 \
    --source=. \
    --no-allow-unauthenticated \
    --region="us-central1" \
    --project="{your-project-id}" \
    --service-account a2a-service-account \
    --set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=true,\
GOOGLE_CLOUD_PROJECT="{your-project-id}",\
GOOGLE_CLOUD_LOCATION="us-central1",\
APP_URL="https://sample-a2a-agent-1234.us-central1.run.app",\
```

### With AlloyDb

```sh
gcloud run deploy sample-a2a-agent \
    --port=8080 \
    --source=. \
    --no-allow-unauthenticated \
    --region="us-central1" \
    --project="{your-project-id}" \
    --update-secrets=DB_USER=alloy_db_user:latest,DB_PASS=alloy_db_pass:latest \
    --service-account a2a-service-account \
    --set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=true,\
GOOGLE_CLOUD_PROJECT="{your-project-id}",\
GOOGLE_CLOUD_LOCATION="us-central1",\
APP_URL="https://sample-a2a-agent-1234.us-central1.run.app",\
USE_ALLOY_DB="True",\
DB_INSTANCE="projects/{your-project-id}/locations/us-central1/clusters/{my-cluster}/instances/primary-instance",\
DB_NAME="postgres"
```

In case the run.app URL, returned by above deploy command, is different from the predefined deterministic URL, then you can update the APP_URL environment variable.

```sh
gcloud run services update --region="us-central1" sample-a2a-agent --update-env-vars APP_URL="{run.app-url}"
```

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
