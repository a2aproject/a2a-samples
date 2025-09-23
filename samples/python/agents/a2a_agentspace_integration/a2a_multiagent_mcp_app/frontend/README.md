# A2A Multi-Agent on Agent Engine

> **⚠️ DISCLAIMER: THIS IS NOT AN OFFICIALLY SUPPORTED GOOGLE PRODUCT. THIS PROJECT IS INTENDED FOR DEMONSTRATION PURPOSES ONLY. IT IS NOT INTENDED FOR USE IN A PRODUCTION ENVIRONMENT.**

## **0. Ceate the .env file**
 Create the .env using the .env.example file
 
## **1. Run it locally**

```bash
uv run main.py
```

## **2. Deploy to Cloud Run**


In Cloud Shell, execute the following command:
```bash
# Define a name for your Cloud Run service
export SERVICE_NAME='adk-frontend'

# Specify the Google Cloud region for deployment (ensure it supports required services)
export LOCATION='us-central1'

# Replace with your Google Cloud Project ID
export PROJECT_ID=''

export PROJECT_NUMBER=''

export AGENT_ENGINE_ID=''
```

In Cloud Shell, execute the following command:


```bash
export $(sed -e '/^ *#/d' -e '/^$/d' -e 's/ *= */=/' -e 's/\\'//g -e 's/"//g' .env | xargs)

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


## **3. (Optional) Register to Agentspace**

The optional step is to make your deployed agent available in AgentSpace.

Get the Reasoning Engine ID: The REASONING_ENGINE_ID is the ID of your Agent Engine instance. 

Update and run the expose script:

Open register_to_agentspace.sh and ensure the REASONING_ENGINE_ID and other variables are set correctly.
Execute the script:
```bash
source regiester_to_agentspace.sh
```
This script registers your Agent Engine instance as a new custom agent.

Use the agent in AgentSpace:

Go to your Google AgentSpace application.
Click on the "Agents" tab.
Your agent will now be available under the "From your organization" section.
Click on it to start a new conversation and interact with your fully deployed, end-to-end agent!
