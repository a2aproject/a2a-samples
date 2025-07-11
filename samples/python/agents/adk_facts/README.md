# ADK Agent

This sample uses the Agent Development Kit (ADK) to create a simple fun facts generator which communicates using A2A and can be deployed to Google Cloud Run.

## Prerequisites

- Python 3.10 or higher
- Access to an LLM and API Key
- If deploying to Cloud Run, you'll need a Google Cloud Project

## Running the Sample

1. Navigate to the samples directory:

    ```bash
    cd samples/python/agents/adk_facts
    ```

2. Install Requirements

    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file with your Gemini API Key:

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

4. Run the remote A2A agent:

    ```bash
    adk api_server --a2a --port 8001 remote_a2a
    ```

5. Run the main agent

    ```bash
    # In a separate terminal, run the adk web server
    adk web samples/python/agents/
    ```

  In the Web UI, select the `adk_facts` agent.

## Deploy to Google Cloud Run

This section guides you through deploying the remote A2A agent as a secure, scalable service on Google Cloud Run. When deployed on Google Cloud, the agent will use a Service Account and Vertex AI for authentication and LLM access, which is more secure and robust than using API keys in a production environment.

### 1. Set Up Your Environment

Set your Google Cloud Project ID and desired region as environment variables.

```bash
# Replace with your Google Cloud Project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# You can choose another region that supports Cloud Run and Vertex AI
export GOOGLE_CLOUD_REGION="us-central1"

# Set your project for all subsequent gcloud commands
gcloud config set project $GOOGLE_CLOUD_PROJECT
```

### 2. Configure Permissions

Your Cloud Run service needs a dedicated identity (a Service Account) with specific permissions to function correctly.

**a. Create a Service Account**

This account will act as the identity of your running service.

```bash
gcloud iam service-accounts create a2a-service-account \
  --display-name="A2A Cloud Run Service Account"
```

**b. Grant IAM Roles**

Grant the service account permission to invoke Vertex AI models. If you were using Secret Manager to store API keys (not needed for this Vertex AI setup), you would also add the `roles/secretmanager.secretAccessor` role.

- `roles/aiplatform.user`: Allows the service to make prediction calls to Vertex AI models.

```bash
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
  --member="serviceAccount:a2a-service-account@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 3. Deploy the Service

This command builds and deploys your agent. We use `--allow-unauthenticated` to make the agent publicly accessible, as required for A2A communication with agents outside your Google Cloud project.

> **Note:** The first time you run this, `gcloud` may prompt you to enable necessary APIs like `run.googleapis.com` and `artifactregistry.googleapis.com`. Answer `y` to proceed.

```bash
gcloud run deploy sample-a2a-agent \
    --port=8080 \
    --source=. \
    --allow-unauthenticated \
    --region="us-central1" \
    --project=$GOOGLE_CLOUD_PROJECT \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION,GOOGLE_GENAI_USE_VERTEXAI=true
```

Your A2A agent is now running on Google Cloud!

Try interacting with the A2A agent by using [A2A Inspector](https://github.com/a2aproject/a2a-inspector).

There's a deployed instance of the Inspector App at <https://a2a-inspector-908687846511.us-central1.run.app/>

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
