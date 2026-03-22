#!/bin/bash
#
# Test Deployed Agents - Simple Wrapper Script
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== AI Creative Studio - Agent Testing ===${NC}\n"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Error: .env file not found"
    echo "Make sure your agent URLs are configured in .env"
    exit 1
fi

# Load Python virtual environment if it exists
if [ -d "$PROJECT_ROOT/agents/brand_strategist/.venv" ]; then
    source "$PROJECT_ROOT/agents/brand_strategist/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Run tests
cd "$SCRIPT_DIR"

case "${1:-all}" in
all)
    echo -e "${YELLOW}Running complete test suite...${NC}\n"
    python3 test_deployed_agents.py --test all
    ;;
specialists)
    echo -e "${YELLOW}Testing specialist agents only...${NC}\n"
    python3 test_deployed_agents.py --test specialists
    ;;
orchestrator | director)
    echo -e "${YELLOW}Testing Creative Director orchestrator...${NC}\n"
    python3 test_deployed_agents.py --test orchestrator
    ;;
strategist | brand)
    echo -e "${YELLOW}Testing Brand Strategist...${NC}\n"
    python3 test_deployed_agents.py --agent "Brand Strategist"
    ;;
copywriter | copy)
    echo -e "${YELLOW}Testing Copywriter...${NC}\n"
    python3 test_deployed_agents.py --agent "Copywriter"
    ;;
designer | design)
    echo -e "${YELLOW}Testing Designer...${NC}\n"
    python3 test_deployed_agents.py --agent "Designer"
    ;;
critic | review)
    echo -e "${YELLOW}Testing Critic...${NC}\n"
    python3 test_deployed_agents.py --agent "Critic"
    ;;
pm | project-manager)
    echo -e "${YELLOW}Testing Project Manager...${NC}\n"
    python3 test_deployed_agents.py --agent "Project Manager"
    ;;
help | --help | -h)
    echo "Usage: ./test_agents.sh [test_type]"
    echo ""
    echo "Test types:"
    echo "  all              - Test all agents (default)"
    echo "  specialists      - Test all specialist agents only"
    echo "  orchestrator     - Test Creative Director only"
    echo "  strategist       - Test Brand Strategist only"
    echo "  copywriter       - Test Copywriter only"
    echo "  designer         - Test Designer only"
    echo "  critic           - Test Critic only"
    echo "  pm               - Test Project Manager only"
    echo ""
    echo "Examples:"
    echo "  ./test_agents.sh                 # Test everything"
    echo "  ./test_agents.sh specialists     # Test only Cloud Run agents"
    echo "  ./test_agents.sh orchestrator    # Test only Creative Director"
    echo "  ./test_agents.sh copywriter      # Test only Copywriter"
    ;;
*)
    echo "Unknown test type: $1"
    echo "Run './test_agents.sh help' for usage"
    exit 1
    ;;
esac
