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

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

4. Run the A2A agent:

    ```bash
    uvicorn agent:a2a_app --host localhost --port 8001
    ```

5. Run the ADK Web Server

    ```bash
    # In a separate terminal, run the adk web server
    adk web samples/python/agents/
    ```

  In the Web UI, select the `adk_facts` agent.

## Deploy to Google Cloud Run

```sh
gcloud run deploy sample-a2a-agent \
    --port=8080 \
    --source=. \
    --allow-unauthenticated \
    --region="us-central1" \
    --project=$GOOGLE_CLOUD_PROJECT \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=true
```
