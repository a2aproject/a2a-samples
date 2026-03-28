# Settlement Extension Implementation

This is the Python implementation of the A2A Settlement Extension defined in
`extensions/settlement/v1`.

## What it does

Adds escrow-based token settlement to A2A agent interactions. Funds are held in
escrow while an agent works on a task, then released on completion or refunded
on failure.

## Quick start

```python
from settlement_ext import SettlementExtension

ext = SettlementExtension(
    exchange_url="https://exchange.a2a-settlement.org/api/v1",
    api_key="ate_your_key",
    account_id="your-agent-uuid",
)

# Add to your AgentCard
card = ext.add_to_card(card, pricing={
    "sentiment-analysis": {"baseTokens": 10, "model": "per-request"}
})

# Server side: wrap your executor to auto-verify escrow
agent_executor = ext.wrap_executor(agent_executor)

# Client side: wrap your client to auto-settle on task completion
client = ext.wrap_client(client)
```

## Usage patterns

The extension provides several integration levels, from fully manual to fully
managed. See the `SettlementExtension` class documentation for all options.

## Live exchange

A public sandbox exchange is available at
<https://exchange.a2a-settlement.org/api/v1> for testing. Register an agent to
get an API key and 100 starter tokens.
