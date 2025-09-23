# Set Up MCP server using Cloud Run

## Setup and Deployment



In your Cloud Shell or local terminal (with gcloud CLI configured), set the following environment variables:

Note: The below parameters need to match with the values in .env file.

```bash
# Define a name for your Cloud Run service
export SERVICE_NAME='weather-remote-mcp-server'

# Specify the Google Cloud region for deployment (ensure it supports required services)
export LOCATION='us-central1'

# Replace with your Google Cloud Project ID
export PROJECT_ID=''

export PROJECT_NUMBER=''
```

In Cloud Shell, execute the following command:


```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $LOCATION \
  --project $PROJECT_ID \
  --memory 4G \
  --no-allow-unauthenticated


```
```
gcloud run services proxy $SERVICE_NAME --region=us-central1
```

## Add Compute User Permission
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region="us-central1"



## Add Cloudtop User Permission (Optional, only if you want to use Cloudtop)
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="serviceAccount:insecure-cloudtop-shared-user@cloudtop-prod-us-west.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region="us-central1"

