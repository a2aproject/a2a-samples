# Hello World Azure AI Foundry Agent Examples

This directory contains additional examples and use cases for the Hello World agent.

## Examples

### Basic Examples

- `simple_chat.py` - Simple one-off conversation
- `multi_turn.py` - Multi-turn conversation example
- `error_handling.py` - Error handling demonstration

### Advanced Examples  

- `streaming_response.py` - Streaming responses (if supported)
- `context_management.py` - Managing conversation context
- `custom_instructions.py` - Using custom instructions

## Running Examples

```bash
# Run a specific example
python examples/simple_chat.py

# Or using uv
uv run python examples/simple_chat.py
```

## Example Descriptions

### simple_chat.py
Demonstrates a basic single interaction with the agent. Good for testing connectivity and basic functionality.

### multi_turn.py
Shows how to maintain a conversation across multiple messages, demonstrating the agent's memory capabilities within a thread.

### error_handling.py
Demonstrates proper error handling for common scenarios like network issues, authentication errors, and malformed requests.

## Creating New Examples

When creating new examples:

1. Import the HelloWorldAgent from the parent directory
2. Use proper error handling
3. Include cleanup code
4. Add documentation comments
5. Test with different scenarios

Example template:

```python
#!/usr/bin/env python3
"""Example: Your example description here."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_agent import HelloWorldAgent


async def main():
    """Your example main function."""
    agent = HelloWorldAgent()
    
    try:
        await agent.create_agent()
        # Your example code here
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await agent.cleanup_agent()


if __name__ == "__main__":
    asyncio.run(main())
```
