# A2A Multi-Agent Frontend

This is the frontend for the A2A Multi-Agent on Agent Engine application.

> **⚠️ DISCLAIMER: THIS IS NOT AN OFFICIALLY SUPPORTED GOOGLE PRODUCT. THIS PROJECT IS INTENDED FOR DEMONSTRATION PURPOSES ONLY. IT IS NOT INTENDED FOR USE IN A PRODUCTION ENVIRONMENT.**

## Prerequisites

Before you begin, ensure you have the following:

*   A Google Cloud project with billing enabled.
*   The [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated.
*   The `uv` Python package manager installed.

## Getting Started

### 1. Create the `.env` file

Create a `.env` file by copying the `.env.example` file.

```bash
cp .env.example .env
```

You will need to fill in the values for `PROJECT_ID`, `PROJECT_NUMBER`, and `AGENT_ENGINE_ID` in the `.env` file. You can get these values from your Google Cloud project.

### 2. Run Locally

To run the application locally, execute the following command:

```bash
uv run main.py
```

The application will be available at `http://127.0.0.1:8080`.

## Deployment to Cloud Run

### 1. Configure Environment Variables

In your Cloud Shell, execute the following commands to set up your environment variables.

```bash
# Define a name for your Cloud Run service
export SERVICE_NAME=\'a2a-frontend'

# Specify the Google Cloud region for deployment
export LOCATION=\'us-central1'

# Replace with your Google Cloud Project ID
export PROJECT_ID=\'your-gcp-project-id'

# Replace with your Google Cloud Project Number
export PROJECT_NUMBER=\'your-gcp-project-number'

# Replace with your Agent Engine ID
export AGENT_ENGINE_ID=\'your-agent-engine-id'
```

### 2. Deploy the Service

Execute the following command to deploy the application to Cloud Run:

In Cloud Shell, execute the following command:


```bash
export $(sed -e '/^ *#/d' -e '/^$/d' -e 's/ *= */=/' -e "s/'//g" -e 's/"//g' .env | xargs)

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $LOCATION \
  --project $PROJECT_ID \
  --memory 4G \
  --no-allow-unauthenticated \
  --update-env-vars=PROJECT_ID=$PROJECT_ID,AGENT_ENGINE_ID=$AGENT_ENGINE_ID,PROJECT_NUMBER=$PROJECT_NUMBER,
```

The Cloud Run is set up not to allow unauthenticated access, so you need to add the invoker role to the Cloud Run service account.

In Cloud Shell, execute the following command to autherize the Cloud Run service

```bash
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region=us-central1 \
    --project=$PROJECT_ID
```

For temporary testing, you can use the following command to authorize all users to the Cloud Run service
```bash
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --region=us-central1 \
    --project=$PROJECT_ID
```

You can then open the Cloud Run service in a browser to access the app.

