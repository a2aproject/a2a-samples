"""
Multi-agent routing application with Azure AI Agents integration.

This application provides a Gradio interface for interacting with a routing agent
that uses Azure AI Agents for core functionality and delegates tasks to remote agents.
"""

import asyncio
import os
import traceback
from collections.abc import AsyncIterator
from pprint import pformat

import gradio as gr

from routing_agent import RoutingAgent

APP_NAME = "azure_routing_app"
USER_ID = "default_user"
SESSION_ID = "default_session"

# Global routing agent instance
ROUTING_AGENT: RoutingAgent = None


async def get_response_from_agent(
    message: str,
    history: list[gr.ChatMessage],
) -> AsyncIterator[gr.ChatMessage]:
    """Get response from Azure AI Foundry Agent routing by A2A and Semantic Kernel."""
    global ROUTING_AGENT
    
    if not ROUTING_AGENT:
        yield gr.ChatMessage(
            role="assistant",
            content="❌ **Error**: Routing agent not initialized. Please restart the application.",
        )
        return
    
    try:
        # Show that we're processing the request
        yield gr.ChatMessage(
            role="assistant",
            content="🤔 **Processing your request...**",
        )
        
        # Process the message through Azure AI Agent
        response = await ROUTING_AGENT.process_user_message(message)
        
        # Yield the final response
        if response:
            yield gr.ChatMessage(
                role="assistant", 
                content=response
            )
        else:
            yield gr.ChatMessage(
                role="assistant",
                content="❌ **Error**: No response received from the agent.",
            )
            
    except Exception as e:
        print(f"Error in get_response_from_agent (Type: {type(e)}): {e}")
        traceback.print_exc()
        yield gr.ChatMessage(
            role="assistant",
            content=f"❌ **An error occurred**: {str(e)}\n\nPlease check the server logs for details.",
        )


async def initialize_routing_agent():
    """Initialize the Azure AI routing agent."""
    global ROUTING_AGENT
    
    try:
        print("Initializing Azure AI routing agent...")
        
        # Create the routing agent with remote agent addresses
        ROUTING_AGENT = await RoutingAgent.create(
            remote_agent_addresses=[
                os.getenv('PLAYWRIGHT_AGENT_URL', 'http://localhost:10001'),
                os.getenv('TOOL_AGENT_URL', 'http://localhost:10002'),
            ]
        )
        
        # Create the Azure AI agent
        azure_agent = ROUTING_AGENT.create_agent()
        print(f"Azure AI routing agent initialized successfully with ID: {azure_agent.id}")
        
    except Exception as e:
        print(f"Failed to initialize routing agent: {e}")
        traceback.print_exc()
        raise


async def cleanup_routing_agent():
    """Clean up the routing agent resources."""
    global ROUTING_AGENT
    
    if ROUTING_AGENT:
        try:
            ROUTING_AGENT.cleanup()
            print("Routing agent cleaned up successfully.")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            ROUTING_AGENT = None


async def main():
    """Main gradio app with Azure AI Agents integration."""
    
    # Check required environment variables
    required_env_vars = [
        "AZURE_AI_AGENT_ENDPOINT",
        "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these environment variables before running the application.")
        return
    
    # Initialize the routing agent
    await initialize_routing_agent()

    try:
        with gr.Blocks(theme=gr.themes.Ocean(), title="Azure AI Routing Agent") as demo:
            # Header section
            gr.Markdown("""
            # 🤖 Azure AI Routing Agent
            
            This assistant uses Azure AI Agents to help you to use playwright and some dev tools.
            The agent intelligently routes your requests to specialized remote agents for optimal assistance.
            """)
            
            # Display agent status
            if ROUTING_AGENT and ROUTING_AGENT.azure_agent:
                gr.Markdown(f"""
                ### 📊 Agent Status
                - **Azure AI Agent ID**: `{ROUTING_AGENT.azure_agent.id}`
                - **Thread ID**: `{ROUTING_AGENT.current_thread.id if ROUTING_AGENT.current_thread else 'Not created'}`
                - **Available Remote Agents**: {len(ROUTING_AGENT.remote_agent_connections)}
                """)
            
            # Chat interface
            gr.ChatInterface(
                get_response_from_agent,
                title="💬 Chat with Azure AI Routing Agent",
                description="Giv me a message, I will hellp you to browse the web, clone repo, or open it with VSCode and VSCode Insiders",
                examples=[
                    "Clone repo https://github.com/kinfey/mcpdemo1",
                    "Go to github.com/kinfey",
                    "Open {path} with VSCode or VSCode Insiders",
                ]
            )
            
            # Footer
            gr.Markdown("""
            ---
            **Powered by**: Azure AI Agents | **A2A Framework**: Multi-Agent Routing System with Semantic Kernel and A2A
            """)

        print("Launching Gradio interface...")
        demo.queue().launch(
            server_name="0.0.0.0",
            server_port=8083,
        )
        
    except Exception as e:
        print(f"Error in main application: {e}")
        traceback.print_exc()
    finally:
        print("Shutting down application...")
        await cleanup_routing_agent()
        print("Gradio application has been shut down.")

if __name__ == "__main__":
    asyncio.run(main())
