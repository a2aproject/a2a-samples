"""Package initialization for Hello World Azure AI Foundry Agent."""

__version__ = "0.1.0"
__author__ = "Azure AI Foundry Team"
__description__ = "A simple Hello World Azure AI Foundry agent example"

from .hello_agent import HelloWorldAgent, create_hello_world_agent

__all__ = ["HelloWorldAgent", "create_hello_world_agent"]
