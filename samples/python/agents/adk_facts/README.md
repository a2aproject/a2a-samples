# ADK Agent

This sample uses the Agent Development Kit (ADK) to create a simple fun facts generator which communicates using A2A.

## Prerequisites

- Python 3.10 or higher
- Access to an LLM and API Key

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

   ```env
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

## Configure Google Cloud Run

### Create Service Account

Cloud Run uses service accounts (SA) when running service instances (link). Create a service account specific for the deployed A2A service.

```sh
gcloud iam service-accounts create a2a-service-account \
  --description="service account for a2a cloud run service" \
  --display-name="A2A cloud run service account"
```

### Add IAM access

The below roles allow the Cloud Run service to access secrets and invoke `predict` API on Vertex AI models.

```sh
gcloud projects add-iam-policy-binding "{your-project-id}" \
  --member="serviceAccount:a2a-service-account@{your-project-id}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
  --role="roles/aiplatform.user"
```

## Deploy to Google Cloud Run

```sh
gcloud run deploy sample-a2a-agent \
    --port=8080 \
    --source=. \
    --allow-unauthenticated \
    --region="us-central1" \
    --project=$GOOGLE_CLOUD_PROJECT \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_REGION=$GOOGLE_CLOUD_REGION,GOOGLE_GENAI_USE_VERTEXAI=true
```

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.
