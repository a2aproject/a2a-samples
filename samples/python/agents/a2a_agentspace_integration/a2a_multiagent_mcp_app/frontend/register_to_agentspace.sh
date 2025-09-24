#!/bin/bash

# Adopted from: https://github.com/sokart/adk-agentengine-agentspace/tree/main

# --- Configuration ---
# TODO: Fill in all placeholder values before running.

export PROJECT_ID="PLACEHOLDER - REPLACE WITH YOUR GOOGLE CLOUD PROJECT ID"
export PROJECT_NUMBER="PLACEHOLDER - REPLACE WITH YOUR GOOGLE CLOUD PROJECT NUMBER"

export REASONING_ENGINE_ID="PLACEHOLDER - REPLACE WITH YOUR AGENT ENGINE ID"
export REASONING_ENGINE_LOCATION="PLACEHOLDER - REPLACE WITH YOUR AGENT ENGINE LOCATION"
export REASONING_ENGINE="projects/${PROJECT_ID}/locations/${REASONING_ENGINE_LOCATION}/reasoningEngines/${REASONING_ENGINE_ID}"

export AS_APP="PLACEHOLDER - REPLACE WITH YOUR AGENT SPACE APPLICATION ID"
export AS_LOCATION="PLACEHOLDER - REPLACE WITH YOUR AGENT SPACE APPLICATION LOCATION"

export AGENT_DISPLAY_NAME="a2a-agent"

AGENT_DESCRIPTION="You're an export of weather and cocktail, answer questions regarding weather and cocktail. You can answer questions like: 1) What is the weather in SF, CA today? 2) What is a good cocktail recipe with gin and lemon? 3) What is the weather like in New York? 4) How to make a Mojito cocktail? 5) What is the weather forecast for this weekend in Los Angeles, CA? 6) Suggest a cocktail recipe for a party? 7) What is the temperature in Tokyo right now? 8) How to make a Margarita cocktail? 9) What is the humidity level in Miami? 10) Recommend a cocktail recipe with vodka and cranberry juice"
export AGENT_DESCRIPTION

DISCOVERY_ENGINE_PROD_API_ENDPOINT="https://discoveryengine.googleapis.com"


# --- Function to Deploy Agent ---
deploy_agent_to_agentspace() {
    echo "🚀 Deploying agent '${AGENT_DISPLAY_NAME}' to project '${PROJECT_ID}'..."

    # Create the JSON payload using a here document to avoid quoting issues
    read -r -d '' JSON_PAYLOAD <<EOF
{
  "displayName": "${AGENT_DISPLAY_NAME}",
  "description": "${AGENT_DESCRIPTION}",
  "icon": {
    "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"
  },
  "adk_agent_definition": {
    "tool_settings": {
      "toolDescription": "${AGENT_DESCRIPTION}"
    },
    "provisioned_reasoning_engine": {
      "reasoningEngine": "${REASONING_ENGINE}"
    }
  }
}
EOF

    curl -X POST \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -H "x-goog-user-project: ${PROJECT_ID}" \
        "${DISCOVERY_ENGINE_PROD_API_ENDPOINT}/v1alpha/projects/${PROJECT_NUMBER}/locations/${AS_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents" \
        -d "${JSON_PAYLOAD}"

    echo -e "\n\n✅ Deployment command finished."
}

# --- Execute Deployment ---
deploy_agent_to_agentspace
