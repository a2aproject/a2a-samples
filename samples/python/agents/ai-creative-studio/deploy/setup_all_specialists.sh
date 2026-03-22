#!/bin/bash
#
# GCP Setup Script for All Specialist Agents
# This script creates service accounts and grants necessary IAM permissions
#

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Loading environment variables from .env file...${NC}"
    set -a
    source <(grep -v '^#' "$ENV_FILE" | grep -v '^[[:space:]]*$' | sed 's/\r$//')
    set +a
    echo -e "${GREEN}.env file loaded${NC}\n"
fi

# Configuration - support both LOCATION and REGION naming conventions
PROJECT_ID="${PROJECT_ID:-devfestahlen}"
REGION="${LOCATION:-${REGION:-us-central1}}"
USER_EMAIL="${USER_EMAIL:-}"

echo -e "${GREEN}=== AI Creative Studio - Complete GCP Setup ===${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current user email if not set
if [ -z "$USER_EMAIL" ]; then
    USER_EMAIL=$(gcloud config get-value account 2>/dev/null)
    if [ -z "$USER_EMAIL" ]; then
        echo -e "${YELLOW}Could not detect user email. Please enter your GCP account email:${NC}"
        read -r USER_EMAIL
    fi
fi

echo -e "${GREEN}Project ID: ${PROJECT_ID}${NC}"
echo -e "${GREEN}Region: ${REGION}${NC}"
echo -e "${GREEN}User Email: ${USER_EMAIL}${NC}\n"

# Confirm before proceeding
echo -e "${YELLOW}This script will:${NC}"
echo "  1. Enable required GCP APIs"
echo "  2. Create 5 service accounts (one for each specialist agent)"
echo "  3. Grant necessary IAM roles to service accounts"
echo "  4. Grant you (${USER_EMAIL}) permission to impersonate service accounts"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Set the project
echo -e "\n${YELLOW}Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "\n${YELLOW}Enabling required GCP APIs...${NC}"
echo -e "${YELLOW}(This may take a few minutes)${NC}\n"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com \
    --project="$PROJECT_ID"

echo -e "${GREEN}APIs enabled successfully${NC}"

# Define all service accounts
declare -A SERVICE_ACCOUNTS=(
    ["brand-strategist-sa"]="Brand Strategist Agent"
    ["copywriter-sa"]="Copywriter Agent"
    ["designer-sa"]="Designer Agent"
    ["critic-sa"]="Critic Agent"
    ["project-manager-sa"]="Project Manager Agent"
)

# Create service accounts and grant permissions
echo -e "\n${YELLOW}Creating service accounts and granting permissions...${NC}\n"

for SA_NAME in "${!SERVICE_ACCOUNTS[@]}"; do
    SA_DISPLAY="${SERVICE_ACCOUNTS[$SA_NAME]}"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

    echo -e "${YELLOW}Processing: ${SA_DISPLAY} (${SA_NAME})${NC}"

    # Create service account
    SA_CREATED=false
    if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
        echo "  ✓ Service account already exists"
    else
        gcloud iam service-accounts create "$SA_NAME" \
            --display-name="$SA_DISPLAY" \
            --project="$PROJECT_ID"
        echo "  ✓ Service account created"
        SA_CREATED=true
    fi

    # Wait for service account propagation if newly created
    if [ "$SA_CREATED" = true ]; then
        echo "  ⏳ Waiting for service account to propagate (10 seconds)..."
        sleep 10

        # Verify service account is ready
        RETRY_COUNT=0
        MAX_RETRIES=5
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
                echo "  ✓ Service account ready"
                break
            fi
            echo "  ⏳ Still propagating... (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
            sleep 5
            RETRY_COUNT=$((RETRY_COUNT+1))
        done
    fi

    # Grant Vertex AI User role to service account
    echo "  → Granting Vertex AI User role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/aiplatform.user" \
        --quiet

    # Grant Secret Manager Secret Accessor role to service account
    echo "  → Granting Secret Manager Secret Accessor role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet

    # Grant user permission to impersonate this service account
    echo "  → Granting you permission to impersonate this service account..."
    gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
        --member="user:$USER_EMAIL" \
        --role="roles/iam.serviceAccountUser" \
        --project="$PROJECT_ID" \
        --quiet

    echo -e "  ${GREEN}✓ ${SA_DISPLAY} setup complete${NC}\n"
done

# Display summary
echo -e "\n${GREEN}=========================================="
echo "=== Setup Complete ===${NC}"
echo -e "${GREEN}==========================================${NC}\n"

echo -e "${GREEN}All 5 specialist agents are ready for deployment!${NC}\n"

echo "Service Accounts Created:"
for SA_NAME in "${!SERVICE_ACCOUNTS[@]}"; do
    echo "  • ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
done

echo ""
echo "Next steps:"
echo -e "  ${YELLOW}1. Deploy all specialist agents to Cloud Run:${NC}"
echo "     cd deploy"
echo "     ./deploy_complete_system.sh"
echo ""
echo -e "  ${YELLOW}2. Or deploy specialists individually:${NC}"
echo "     cd agents/[agent_name]"
echo "     ./deploy/deploy.sh"
echo ""
