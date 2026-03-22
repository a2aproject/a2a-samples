#!/bin/bash

# GCP Teardown Script for Brand Strategist A2A Agent
# This script removes the deployed agent and cleans up GCP resources

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration variables
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="brand-strategist"
SERVICE_ACCOUNT_NAME="brand-strategist-sa"

echo -e "${RED}=== Brand Strategist A2A Agent - GCP Teardown ===${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
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

echo -e "${YELLOW}This will delete the following resources:${NC}"
echo -e "  - Cloud Run service: ${SERVICE_NAME}"
echo -e "  - Service account: ${SERVICE_ACCOUNT_NAME}"
echo -e "  - IAM policy bindings"
echo -e "\n${RED}This action cannot be undone!${NC}"
echo -e "${YELLOW}Do you want to continue? (yes/no):${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${GREEN}Teardown cancelled${NC}"
    exit 0
fi

# Set the project
gcloud config set project "$PROJECT_ID"

# Delete Cloud Run service
echo -e "\n${YELLOW}Deleting Cloud Run service...${NC}"
if gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    gcloud run services delete "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet
    echo -e "${GREEN}Cloud Run service deleted${NC}"
else
    echo -e "${YELLOW}Cloud Run service not found, skipping${NC}"
fi

# Remove IAM policy bindings
echo -e "\n${YELLOW}Removing IAM policy bindings...${NC}"
gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user" \
    --quiet 2>/dev/null || true

gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || true

echo -e "${GREEN}IAM policy bindings removed${NC}"

# Delete service account
echo -e "\n${YELLOW}Deleting service account...${NC}"
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
    gcloud iam service-accounts delete "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --project="$PROJECT_ID" \
        --quiet
    echo -e "${GREEN}Service account deleted${NC}"
else
    echo -e "${YELLOW}Service account not found, skipping${NC}"
fi

echo -e "\n${GREEN}=== Teardown Complete ===${NC}\n"
echo -e "${GREEN}All resources have been removed${NC}"
