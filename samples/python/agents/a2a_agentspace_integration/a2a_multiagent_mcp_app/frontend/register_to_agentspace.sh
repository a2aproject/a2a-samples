#!/bin/bash

# This script deploys an agent to AgentSpace.

set -euo pipefail

usage() {
  echo "Usage: $0 [ -h | --help ] [ -v | --version ] [ -d | --dry-run ] [ -f | --force ] [ -q | --quiet ] [ -l | --log-file <log_file> ] [ -c | --config-file <config_file> ]"
  echo ""
  echo "Options:"
  echo "  -h, --help            Show this help message and exit."
  echo "  -v, --version         Show the version of this script and exit."
  echo "  -d, --dry-run         Show the curl command without executing it."
  echo "  -f, --force           Skip the confirmation prompt."
  echo "  -q, --quiet           Suppress all output except for errors."
  echo "  -l, --log-file        Write the output to a log file."
  echo "  -c, --config-file     Read the environment variables from a config file."
}

main() {
  # Parse the command line arguments
  while [[ $# -gt 0 ]]
  do
    key="$1"
    case $key in
      -h|--help)
        usage
        exit 0
        ;; 
      -v|--version)
        echo "$0 version 1.0.0"
        exit 0
        ;; 
      -d|--dry-run)
        DRY_RUN=true
        ;; 
      -f|--force)
        FORCE=true
        ;; 
      -q|--quiet)
        QUIET=true
        ;; 
      -l|--log-file)
        LOG_FILE="$2"
        shift
        ;; 
      -c|--config-file)
        CONFIG_FILE="$2"
        shift
        ;; 
      *)
        # unknown option
        ;;
    esac
    shift
  done

  # Load config file if provided
  if [ -n "${CONFIG_FILE:-}" ]; then
    if [ -f "${CONFIG_FILE}" ]; then
      source "${CONFIG_FILE}"
    else
      echo "Config file not found: ${CONFIG_FILE}"
      exit 1
    fi
  fi

  # Check for required commands
  if ! command -v gcloud &> /dev/null
  then
    echo "gcloud could not be found"
    exit
  fi

  if ! command -v curl &> /dev/null
  then
    echo "curl could not be found"
    exit
  fi

  # Check for required environment variables
  if [ -z "${PROJECT_ID:-}" ]; then
    echo "PROJECT_ID is not set"
    exit 1
  fi

  if [ -z "${PROJECT_NUMBER:-}" ]; then
    echo "PROJECT_NUMBER is not set"
    exit 1
  fi

  if [ -z "${REASONING_ENGINE_ID:-}" ]; then
    echo "REASONING_ENGINE_ID is not set"
    exit 1
  fi

  if [ -z "${REASONING_ENGINE_LOCATION:-}" ]; then
    echo "REASONING_ENGINE_LOCATION is not set"
    exit 1
  fi

  if [ -z "${AS_APP:-}" ]; then
    echo "AS_APP is not set"
    exit 1
  fi

  if [ -z "${AS_LOCATION:-}" ]; then
    echo "AS_LOCATION is not set"
    exit 1
  fi

  export REASONING_ENGINE="projects/${PROJECT_ID}/locations/${REASONING_ENGINE_LOCATION}/reasoningEngines/${REASONING_ENGINE_ID}"

  export AGENT_DISPLAY_NAME="a2a-agent" # String - this will appear as the name of the agent into your AgentSpace
  AGENT_DESCRIPTION=$(cat <<EOF
 You're an export of weather and cocktail, answer questions regarding weather and cocktail. You can answer questions like: 1) What is the weather in SF, CA today? 2) What is a good cocktail recipe with gin and lemon? 3) What is the weather like in New York? 4) How to make a Mojito cocktail? 5) What is the weather forecast for this weekend in Los Angeles, CA? 6) Suggest a cocktail recipe for a party? 7) What is the temperature in Tokyo right now? 8) How to make a Margarita cocktail? 9) What is the humidity level in Miami? 10) Recommend a cocktail recipe with vodka and cranberry juice
EOF
)
  export AGENT_DESCRIPTION

  DISCOVERY_ENGINE_PROD_API_ENDPOINT="https://discoveryengine.googleapis.com"


  deploy_agent_to_agentspace() {
      if [ -z "${DRY_RUN:-}" ]; then
        if [ -z "${FORCE:-}" ]; then
          read -p "Are you sure you want to deploy the agent to AgentSpace? [y/N] " -n 1 -r
          echo
          if [[ ! $REPLY =~ ^[Yy]$ ]]
          then
            exit 1
          fi
        fi
      fi

      CURL_COMMAND="curl -X POST \
          -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \
          -H \"Content-Type: application/json\" \
          -H \"x-goog-user-project: ${PROJECT_ID}\" \
          \"${DISCOVERY_ENGINE_PROD_API_ENDPOINT}/v1alpha/projects/${PROJECT_NUMBER}/locations/${AS_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents\" \
          -d '{ 
        \"name\": \"projects/${PROJECT_NUMBER}/locations/${AS_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant\", 
        \"displayName\": \"${AGENT_DISPLAY_NAME}\", 
        \"description\": \"${AGENT_DESCRIPTION}\", 
        \"icon\": { 
          \"uri\": \"https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg\" 
        }, 
        \"adk_agent_definition\": { 
          \"tool_settings\": { 
            \"toolDescription\": \"${AGENT_DESCRIPTION}\" 
          }, 
          \"provisioned_reasoning_engine\": { 
            \"reasoningEngine\": \"${REASONING_ENGINE}\" 
          } 
        } 
      }'"

      if [ -n "${DRY_RUN:-}" ]; then
        echo "${CURL_COMMAND}"
      else
        if [ -n "${QUIET:-}" ]; then
          eval "${CURL_COMMAND}" > /dev/null
        elif [ -n "${VERBOSE:-}" ]; then
          echo "${CURL_COMMAND}"
          eval "${CURL_COMMAND}"
        elif [ -n "${LOG_FILE:-}" ]; then
          eval "${CURL_COMMAND}" >> "${LOG_FILE}"
        else
          eval "${CURL_COMMAND}"
        fi
      fi
  }

  deploy_agent_to_agentspace
}

main "$@"
