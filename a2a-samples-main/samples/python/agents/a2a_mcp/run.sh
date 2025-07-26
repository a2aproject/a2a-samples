#!/bin/bash

# A script to automate the execution of the a2a_mcp example.
# It starts all necessary servers and agents in the background,
# runs the client, and then cleans up all background processes.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# The main working directory for the example
WORK_DIR="samples/python/agents/a2a_mcp"
# Directory to store log files for background processes
LOG_DIR="logs"


# --- Cleanup Function ---
# This function is called automatically when the script exits (for any reason)
# to ensure all background processes are terminated.
cleanup() {
    echo ""
    echo "Shutting down background processes..."
    # Check if the pids array is not empty
    if [ ${#pids[@]} -ne 0 ]; then
        # Kill all processes using their PIDs stored in the array.
        # The 2>/dev/null suppresses "Terminated" messages or errors if a process is already gone.
        kill "${pids[@]}" 2>/dev/null
        wait "${pids[@]}" 2>/dev/null
    fi
    echo "Cleanup complete."
}

# Trap the EXIT signal to call the cleanup function. This ensures cleanup
# runs whether the script finishes successfully, fails, or is interrupted.
trap cleanup EXIT


# --- Main Script Logic ---

# Check if the working directory exists.
if [ ! -d "$WORK_DIR" ]; then
    echo "Error: Directory '$WORK_DIR' not found."
    echo "Please run this script from the root of the repository."
    exit 1
fi

# Navigate into the working directory.
cd "$WORK_DIR"
echo "Changed directory to $(pwd)"

# Create a directory for log files if it doesn't exist.
mkdir -p "$LOG_DIR"

echo "Setting up Python virtual environment with 'uv'..."
uv venv

# Activate the virtual environment for the script and all its child processes.
source .venv/bin/activate
echo "Virtual environment activated."

# Array to store Process IDs (PIDs) of background jobs.
pids=()

# --- Start Background Services ---
echo ""
echo "Starting servers and agents in the background..."

# 1. Start MCP Server
echo "-> Starting MCP Server (Port: 10100)... Log: $LOG_DIR/mcp_server.log"
uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100 > "$LOG_DIR/mcp_server.log" 2>&1 &
pids+=($!)

# 2. Start Orchestrator Agent
echo "-> Starting Orchestrator Agent (Port: 10101)... Log: $LOG_DIR/orchestrator_agent.log"
uv run --env-file .env src/a2a_mcp/agents/ --agent-card agent_cards/orchestrator_agent.json --port 10101 > "$LOG_DIR/orchestrator_agent.log" 2>&1 &
pids+=($!)

# 3. Start Planner Agent
echo "-> Starting Planner Agent (Port: 10102)... Log: $LOG_DIR/planner_agent.log"
uv run --env-file .env src/a2a_mcp/agents/ --agent-card agent_cards/planner_agent.json --port 10102 > "$LOG_DIR/planner_agent.log" 2>&1 &
pids+=($!)

# 4. Start Airline Ticketing Agent
echo "-> Starting Airline Agent (Port: 10103)... Log: $LOG_DIR/airline_agent.log"
uv run --env-file .env src/a2a_mcp/agents/ --agent-card agent_cards/air_ticketing_agent.json --port 10103 > "$LOG_DIR/airline_agent.log" 2>&1 &
pids+=($!)

# 5. Start Hotel Reservations Agent
echo "-> Starting Hotel Agent (Port: 10104)... Log: $LOG_DIR/hotel_agent.log"
uv run --env-file .env src/a2a_mcp/agents/ --agent-card agent_cards/hotel_booking_agent.json --port 10104 > "$LOG_DIR/hotel_agent.log" 2>&1 &
pids+=($!)

# 6. Start Car Rental Reservations Agent
echo "-> Starting Car Rental Agent (Port: 10105)... Log: $LOG_DIR/car_rental_agent.log"
uv run --env-file .env src/a2a_mcp/agents/ --agent-card agent_cards/car_rental_agent.json --port 10105 > "$LOG_DIR/car_rental_agent.log" 2>&1 &
pids+=($!)

echo ""
echo "All services are starting. Waiting 10 seconds for them to initialize..."
sleep 10

# --- Run the Foreground Client ---
echo ""
echo "---------------------------------------------------------"
echo "Starting CLI Client..."
echo "The script will exit after the client finishes."
echo "---------------------------------------------------------"
echo ""

# 7. Start the CLI client in the foreground.
# The script will pause here until this command completes.
uv run --env-file .env src/a2a_mcp/mcp/client.py --resource "resource://agent_cards/list" --find_agent "I would like to plan a trip to France."

echo ""
echo "---------------------------------------------------------"
echo "CLI client finished."
echo "---------------------------------------------------------"

# The 'trap' will now trigger the 'cleanup' function automatically upon exiting.
