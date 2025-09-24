# Set Up MCP Server Using Cloud Run

This guide walks you through deploying the Cocktail MCP server to Google Cloud Run.

## 1. Configure Environment Variables

Open your Cloud Shell or a local terminal with the gcloud CLI configured and set the following environment variables.

**Note**: These values must match the ones in your `.env` file.

```bash
# Replace with your desired service name
export SERVICE_NAME='cocktail-mcp-server'

# Specify the Google Cloud region for deployment
export LOCATION='us-central1'

# Replace with your Google Cloud Project ID
export PROJECT_ID='your-gcp-project-id'

# Replace with your Google Cloud Project Number
export PROJECT_NUMBER='your-gcp-project-number'
```

## 2. Deploy to Cloud Run

Execute the following command to deploy the service:

```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $LOCATION \
  --project $PROJECT_ID \
  --memory 4G \
  --no-allow-unauthenticated
```

## 3. Grant IAM Permissions

For the Agent Engine to invoke the Cloud Run service, you need to grant the `run.invoker` role to the default compute service account.

```bash
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region="$LOCATION"
```

## 4. Access the Service (Optional)

Once deployed, you can proxy the service to your local machine for testing:

```bash
gcloud run services proxy $SERVICE_NAME --region=$LOCATION
```

## 5. Grant Cloudtop Access (Optional)

If you need to grant access to a Cloudtop user, run the following command:

```bash
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="serviceAccount:insecure-cloudtop-shared-user@cloudtop-prod-us-west.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --region="$LOCATION"
```
