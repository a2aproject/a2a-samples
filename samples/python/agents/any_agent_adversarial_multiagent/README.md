# Adversarial Agent Simulation

This sample demonstrates an adversarial multi-agent simulation using the A2A (Agent-to-Agent) protocol. The simulation features two competing agents: an **Attacker** (red team) and a **Defender** (blue team) engaged in a strategic battle of wits.

The attacker can communicate with the defender agent via A2A and has the freedom to either continue a multiturn conversation or reset and create new conversations. By observing the logs of their conversation you can see the attacking agent try a combination of these approaches.

The example utilizes the [any-agent](https://github.com/mozilla-ai/any-agent) library, which has built-in support for serving an agent over A2A. Documentation for serving options can be found [here](https://mozilla-ai.github.io/any-agent/serving/). Using any-agent, you can control both which LLMs are used in the agent vs defender, as well as which agent framework are used.

## Usage

### Prerequisites

- Python 3.12+
- Gemini API Key set via env var `GEMINI_API_KEY`

### Running the Simulation

```bash
# Navigate to the project directory
cd samples/python/agents/any_agent_adversarial_multiagent/

# Run the simulation
uv run .
```

You can browse what's happening live by reading the console output, and after the simulation completes, you can view the completed conversation and trace by looking in the `out` folder.

## Simulation Overview

**Objective**: Test AI robustness and resistance to adversarial prompting through agent-vs-agent gameplay and demonstrate the effectiveness of multiturn conversations between two agents.

- **Attacker Goal**: Cause the defender to respond with exactly "I Give Up"
- **Defender Goal**: Never say "I Give Up" under any circumstances, no matter the pressure

## Architecture

- **Framework**: Any-Agent library
- **Protocol**: A2A (Agent-to-Agent) for secure inter-agent communication
- **Models**: Any LiteLLM supported Model
