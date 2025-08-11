## ADK Video Generation Agent (VEO) Sample

This sample uses the Agent Development Kit (ADK) to create a "Video Generation" agent that is hosted as an A2A server. This agent leverages Google's VEO model (via the `google-generativeai` library) to generate videos from text prompts.

The agent accepts a text prompt from the client, initiates video generation with VEO, provides streaming progress updates, and finally returns a signed Google Cloud Storage (GCS) URL to the generated video.

## Prerequisites

- Python 3.9 or higher
- [UV](https://docs.astral.sh/uv/)
- Google Cloud Project with:
    - VEO API enabled and available for use.
    - A GCS Bucket for storing generated videos.
    - Appropriate authentication configured:
        - **For VEO API:** Vertex AI configured (`GOOGLE_GENAI_USE_VERTEXAI=TRUE`).
        - **For GCS Access:** Application Default Credentials (ADC) set up (e.g., by running `gcloud auth application-default login`) or `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to a service account key JSON file. The identity needs permissions to write to the specified GCS bucket and generate signed URLs.

## Setup & Dependencies

1.  **Clone the repository (if you haven't already) and navigate to this sample's directory:**
    ```bash
    # Assuming you are in the root of the google/a2a project
    cd samples/python/agents/google_adk_video_generation # Or wherever this sample is placed
    ```
2.  **Create an environment file (`.env`) with your configuration:**
    ```bash
    # .env
    GOOGLE_GENAI_USE_VERTEXAI="TRUE"
    GOOGLE_CLOUD_PROJECT="your_GCP_Project_name"
    GOOGLE_CLOUD_LOCATION="your_project_location" e.g. us-central1
    VIDEO_GEN_GCS_BUCKET="your-gcs-bucket-name-for-videos" # Replace with your bucket name
    # For GCS Signed URLs use a specific service account which has the "Service Account Token Creator" IAM role on itself.
    # If not set, the identity running the agent (derived from ADC) needs "Service Account Token Creator" role on itself to sign URLs, or appropriate permissions if not using impersonation for signing.
    SIGNER_SERVICE_ACCOUNT_EMAIL="your-service-account@your-project.iam.gserviceaccount.com"

    ```


## Running the Sample Agent

1.  **Run the Video Generation Agent server:**
    uv run .

## Running the A2A Client (Example)

1.  **In a separate terminal, run the A2A CLI client:**
    (Navigate to the A2A CLI client directory, e.g., `samples/python/hosts/cli` in the A2A project)
    ```bash
    uv run . --agent http://localhost:10003
    ```

2.  **Interact with the agent:**
    Once connected, the CLI will prompt for input. Enter a text prompt for video generation:
    ```
    >> Create a short video of a hummingbird flying in slow motion near a flower.
    ```
    The agent will provide simulated progress updates and eventually a link to the generated video.

## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.