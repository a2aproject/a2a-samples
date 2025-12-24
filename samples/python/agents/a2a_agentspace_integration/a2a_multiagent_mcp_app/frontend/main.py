import asyncio
import os
import traceback
from collections.abc import AsyncIterator

import gradio as gr
from dotenv import load_dotenv
from google.adk.sessions import InMemorySessionService
from vertexai import agent_engines

load_dotenv()

APP_NAME = "routing_app"
USER_ID = "default_user"
SESSION_ID = "default_session"
SESSION_SERVICE = InMemorySessionService()

PROJECT_ID = os.getenv("PROJECT_ID")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
PROJECT_NUMBER = os.getenv("PROJECT_NUMBER")

resource_name = f"projects/{PROJECT_NUMBER}/locations/us-central1/reasoningEngines/{AGENT_ENGINE_ID}"

remote_agent = agent_engines.get(resource_name)


async def get_response_from_agent(
    message: str,
    history: list[gr.ChatMessage],
) -> AsyncIterator[gr.ChatMessage]:
    """Get response from host agent."""
    try:
        remote_session = await remote_agent.async_create_session(user_id="user1")
        async for event in remote_agent.async_stream_query(
            user_id="user1",
            session_id=remote_session["id"],
            message=message,
        ):
            if event["content"] and event["content"]["parts"]:
                for part in event["content"]["parts"]:
                    if part.get("text"):
                        yield gr.ChatMessage(role="assistant", content=part["text"])
                    break
    except Exception as e:
        print(f"Error in get_response_from_agent (Type: {type(e)}): {e}")
        traceback.print_exc()  # This will print the full traceback
        yield gr.ChatMessage(
            role="assistant",
            content="An error occurred while processing your request. Please check the server logs for details.",
        )


async def main():
    """Main gradio app."""
    print("Creating ADK session...")
    await SESSION_SERVICE.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print("ADK session created successfully.")

    with gr.Blocks(theme=gr.themes.Ocean(), title="A2A Host Agent with Logo") as demo:
        gr.Image(
            "https://a2a-protocol.org/latest/assets/a2a-logo-black.svg",
            width=100,
            height=100,
            scale=0,
            show_label=False,
            show_download_button=False,
            container=False,
            show_fullscreen_button=False,
        )
        gr.ChatInterface(
            get_response_from_agent,
            title="A2A Host Agent",
            description="This assistant can help you to check weather and find cocktail information",
        )

    print("Launching Gradio interface...")
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=8080,
    )
    print("Gradio application has been shut down.")


if __name__ == "__main__":
    asyncio.run(main())