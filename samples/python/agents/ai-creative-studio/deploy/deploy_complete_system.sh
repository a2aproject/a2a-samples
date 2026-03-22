#!/bin/bash
# Complete System Deployment - One command to deploy everything
# Deploys all 5 specialist agents + Creative Director orchestrator

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AI Creative Studio - Complete Deployment ===${NC}\n"

# Check prerequisites
if ! command -v gcloud &>/dev/null; then
    echo -e "${RED}Error: gcloud CLI not installed${NC}"
    echo "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: Python 3 not installed${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Check for .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${YELLOW}Warning: No .env file found${NC}"
    echo "Please create .env file with PROJECT_ID and LOCATION"
    echo ""
    echo "You can copy .env.example:"
    echo "  cp .env.example .env"
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Load environment variables from .env file
    echo -e "${GREEN}Loading environment variables from .env...${NC}"
    set -a
    source <(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^[[:space:]]*$' | sed 's/\r$//')
    set +a
    echo -e "${GREEN}Environment variables loaded${NC}"

    # Display key configuration (without exposing sensitive data)
    if [[ -n "$NOTION_API_KEY" ]] && [[ -n "$NOTION_DATABASE_ID" ]]; then
        echo -e "${GREEN}✓ Notion credentials found - project-manager will have Notion integration${NC}"
    else
        echo -e "${YELLOW}⚠ Notion credentials not found - project-manager will work without Notion integration${NC}"
    fi
    echo ""
fi

# Run complete deployment
echo -e "${YELLOW}Starting complete system deployment...${NC}"
echo -e "${YELLOW}This will:${NC}"
echo -e "${YELLOW}  1. Deploy all 5 specialist agents to Cloud Run (parallel)${NC}"
echo -e "${YELLOW}  2. Collect agent URLs${NC}"
echo -e "${YELLOW}  3. Deploy Creative Director to Agent Engine${NC}"
echo ""
echo -e "${YELLOW}Estimated time: 10-15 minutes${NC}"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo -e "${GREEN}Starting deployment...${NC}\n"

# Run the orchestrator deployment with auto-deploy flag
python3 "$SCRIPT_DIR/deploy_orchestrator.py" \
    --action deploy \
    --auto-deploy-specialists

# Check if deployment was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
    echo -e "${GREEN}✓ All specialist agents deployed to Cloud Run${NC}"
    echo -e "${GREEN}✓ Creative Director deployed to Agent Engine${NC}"
    echo ""
    echo -e "${GREEN}Your AI Creative Studio is ready!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Test the system:"
    echo "     ./test_agents.sh orchestrator"
    echo ""
else
    echo ""
    echo -e "${RED}=== Deployment Failed ===${NC}"
    echo -e "${RED}Please check the error messages above${NC}"
    exit 1
fi
