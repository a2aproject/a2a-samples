# ADK Agent

This sample uses the Agent Development Kit (ADK) to create a simple calendar update Agent which communicates using A2A.

## Prerequisites

- Python 3.10 or higher
- [UV](https://docs.astral.sh/uv/)
- Access to an LLM and API Key

## Running the Sample

1. Navigate to the samples directory:

```shell
cd samples/python/agents/adk_cloud_run
````

2. Create an environment file with your API key:

```shell
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

3. Run an agent:

```shell
uv run .
```

## Setup Config Google Cloud Run

### Create Service Account

Cloud Run uses [service accounts (SA)](https://cloud.google.com/run/docs/configuring/service-accounts) when running service instances. Create a service account specific for the deployed A2A service.

```shell
gcloud iam service-accounts create a2a-service-account \
  --description="service account for a2a cloud run service" \
  --display-name="A2A cloud run service account"
```

### Add IAM access

Below roles allow cloud run service to access secrets and invoke `predict` API on Vertex AI models.

```shell
gcloud projects add-iam-policy-binding "{your-project-id}" \
  --member="serviceAccount:a2a-service-account@{your-project-id}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --role="roles/aiplatform.user"
```

If using AlloyDb, then also add below IAM role bindings.

```shell
gcloud projects add-iam-policy-binding "{your-project-id}" \
  --member="serviceAccount:a2a-service-account@{your-project-id}.iam.gserviceaccount.com" \
  --role="roles/alloydb.client" \
  --role="roles/serviceusage.serviceUsageConsumer" \
  --role="roles/secretmanager.secretAccessor"
```

### Configure Secrets

All sensitive credentials should be provided to the server using a secure mechanism. Cloud run allows secrets to be provided as environment variables or dynamic volume mounts. DB user & password secrets can be created in Secret Manager as below:

```shell
gcloud secrets create alloy_db_user --replication-policy="automatic"
# Create a file user.txt with contents of secret value
gcloud secrets versions add alloy_db_user --data-file="user.txt"

gcloud secrets create alloy_db_pass --replication-policy="automatic"
# Create a file pass.txt with contents of secret value
gcloud secrets versions add alloy_db_pass --data-file="pass.txt"
```

## Deploy to Google Cloud Run

The A2A cloud run service can be [exposed publicly](https://cloud.google.com/run/docs/authenticating/public) or kept internal to just GCP clients.

When deploying a service to Cloud Run, it returns a `run.app` URL to query the running service.

### Service Authentication

#### IAM based Authentication

IAM can be used for [service-to-service authentication](https://cloud.google.com/run/docs/authenticating/service-to-service) if the clients are within GCP. Agentspace is one such example of an internal client. The clients can use service accounts and they need to be given IAM role: `roles/run.invoker`

#### Public Access

The A2A server is responsible for handling agent level auth. They need to provide this auth info in their agent card using the securitySchemes and security params.

Use the param `--allow-unauthenticated` while deploying to cloud run, to allow public access.

### With `InMemoryTaskStore`

```shell
gcloud run deploy sample-a2a-agent \
    --port=8080 \
    --source=. \
    --no-allow-unauthenticated \
    --memory "1Gi" \
    --region="us-central1" \
    --project="{your-project-id}" \
    --service-account a2a-service-account \
    --set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=true,\
GOOGLE_CLOUD_PROJECT="{your-project-id}",\
GOOGLE_CLOUD_LOCATION="us-central1",\
APP_URL="TEMPORARY_URL"

```

### With AlloyDb

```shell
gcloud run deploy sample-a2a-agent \
    --port=8080 \
    --source=. \
    --no-allow-unauthenticated \
    --memory "1Gi" \
    --region="us-central1" \
    --project="{your-project-id}" \
    --update-secrets=DB_USER=alloy_db_user:latest,DB_PASS=alloy_db_pass:latest \
    --service-account a2a-service-account \
    --set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=true,\
GOOGLE_CLOUD_PROJECT="{your-project-id}",\
GOOGLE_CLOUD_LOCATION="us-central1",\
USE_ALLOY_DB="True",\
DB_INSTANCE="projects/{your-project-id}/locations/us-central1/clusters/{my-cluster}/instances/primary-instance",\
DB_NAME="postgres",\
APP_URL="TEMPORARY_URL"
```

### Update Service with the Service URL

After the deploy command completes, it will output the service URL. Update the running service to set the `APP_URL` environment variable with this new URL.

```shell
gcloud run services update sample-a2a-agent \
  --project="{your-project-id}" \
  --region="us-central1" \
  --update-env-vars=APP_URL="{your-cloud-run-service-url}"
```

## Testing your Agent

You can test your live agent with the A2A CLI, available at `a2a-samples/samples/python/hosts/cli`.

The following command allows you to authenticate and interact with your A2A enabled agent in Cloud Run.

```shell
cd /path/to/cli
uv run . --agent {your-cloud-run-service-url} --bearer-token "$(gcloud auth print-identity-token)
```

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input.

For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks. Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
