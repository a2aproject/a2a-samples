#!/bin/bash

# GCP Initial Setup Script for Brand Strategist A2A Agent
# This script sets up the GCP infrastructure (run once)

set -e # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../brand_strategist/.env"

if [ -f "$ENV_FILE" ]; then
	echo -e "${GREEN}Loading environment variables from .env file...${NC}"
	# Export variables from .env file, ignoring comments and empty lines
	set -a
	# shellcheck source=/dev/null
	source <(grep -v '^#' "$ENV_FILE" | grep -v '^[[:space:]]*$' | sed 's/\r$//')
	set +a
	echo -e "${GREEN}.env file loaded${NC}\n"
else
	echo -e "${YELLOW}No .env file found at $ENV_FILE${NC}"
	echo -e "${YELLOW}Will use environment variables or prompt for values${NC}\n"
fi

# Configuration variables (can be overridden by .env or environment)
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_ACCOUNT_NAME="${GCP_SERVICE_ACCOUNT_NAME:-brand-strategist-sa}"

echo -e "${GREEN}=== Brand Strategist A2A Agent - GCP Setup ===${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &>/dev/null; then
	echo -e "${RED}Error: gcloud CLI is not installed${NC}"
	echo "Please install it from: https://cloud.google.com/sdk/docs/install"
	exit 1
fi

# Prompt for project ID if not set
if [ -z "$PROJECT_ID" ]; then
	echo -e "${YELLOW}Enter your GCP Project ID:${NC}"
	read -r PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
	echo -e "${RED}Error: Project ID is required${NC}"
	exit 1
fi

echo -e "${GREEN}Using Project ID: ${PROJECT_ID}${NC}"
echo -e "${GREEN}Using Region: ${REGION}${NC}\n"

# Set the project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "\n${YELLOW}Enabling required GCP APIs...${NC}"
echo -e "${YELLOW}(This may take a few minutes)${NC}\n"
gcloud services enable run.googleapis.com \
	cloudbuild.googleapis.com \
	secretmanager.googleapis.com \
	aiplatform.googleapis.com \
	--project="$PROJECT_ID"

echo -e "${GREEN}APIs enabled successfully${NC}"

# Create service account
echo -e "\n${YELLOW}Creating service account...${NC}"
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
	echo -e "${GREEN}Service account already exists${NC}"
else
	gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
		--display-name="Brand Strategist Agent Service Account" \
		--project="$PROJECT_ID"
	echo -e "${GREEN}Service account created${NC}"
fi

# Grant IAM roles
echo -e "\n${YELLOW}Granting IAM roles to service account...${NC}"

# Vertex AI User role
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
	--member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
	--role="roles/aiplatform.user" \
	--quiet

# Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
	--member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
	--role="roles/secretmanager.secretAccessor" \
	--quiet

echo -e "${GREEN}IAM roles granted${NC}"

# Display next steps
echo -e "\n${GREEN}=== Setup Complete ===${NC}\n"
echo -e "${GREEN}Your GCP infrastructure is ready!${NC}\n"
echo -e "Service Account: ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com\n"
echo -e "To deploy the agent, run:\n"
echo -e "  ${YELLOW}./deploy/deploy.sh${NC}\n"
