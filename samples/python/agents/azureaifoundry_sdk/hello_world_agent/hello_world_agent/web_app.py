"""Starlette web application for the Hello World Azure AI Foundry Agent."""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket
import uvicorn

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .hello_agent import HelloWorldAgent
from .mock_agent import create_mock_agent
from .utils import validate_environment, format_error_message


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if we're in demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Global storage for agents and sessions
active_agents: Dict[str, HelloWorldAgent] = {}
active_sessions: Dict[str, str] = {}  # session_id -> thread_id

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


async def homepage(request):
    """Serve the main chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})


async def health_check(request):
    """Health check endpoint."""
    if DEMO_MODE:
        return JSONResponse({
            "status": "healthy",
            "mode": "demo",
            "message": "Running in demo mode - no Azure credentials required"
        })
    
    env_check = validate_environment()
    
    return JSONResponse({
        "status": "healthy" if env_check["valid"] else "unhealthy",
        "mode": "azure",
        "environment_valid": env_check["valid"],
        "missing_vars": env_check.get("missing_vars", []),
        "warnings": env_check.get("warnings", [])
    })


async def create_session(request):
    """Create a new chat session."""
    try:
        session_id = str(uuid.uuid4())
        
        # Create appropriate agent based on mode
        if DEMO_MODE:
            agent = await create_mock_agent()
        else:
            agent = HelloWorldAgent()
            await agent.create_agent()
        
        # Create a conversation thread
        thread = await agent.create_thread()
        
        # Store the agent and session
        active_agents[session_id] = agent
        active_sessions[session_id] = thread.id
        
        logger.info(f"Created new session: {session_id} ({'demo' if DEMO_MODE else 'azure'} mode)")
        
        return JSONResponse({
            "session_id": session_id,
            "thread_id": thread.id,
            "status": "created",
            "mode": "demo" if DEMO_MODE else "azure"
        })
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return JSONResponse({
            "error": format_error_message(e)
        }, status_code=500)


async def send_message(request):
    """Send a message to the agent."""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        message = data.get("message", "").strip()
        
        if not session_id or session_id not in active_agents:
            return JSONResponse({
                "error": "Invalid or expired session"
            }, status_code=400)
        
        if not message:
            return JSONResponse({
                "error": "Message cannot be empty"
            }, status_code=400)
        
        agent = active_agents[session_id]
        thread_id = active_sessions[session_id]
        
        # Send message and get response
        responses = await agent.run_conversation(thread_id, message)
        
        return JSONResponse({
            "responses": responses,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return JSONResponse({
            "error": format_error_message(e)
        }, status_code=500)


async def delete_session(request):
    """Delete a chat session and cleanup resources."""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if session_id and session_id in active_agents:
            # Cleanup agent
            agent = active_agents[session_id]
            await agent.cleanup_agent()
            
            # Remove from storage
            del active_agents[session_id]
            del active_sessions[session_id]
            
            logger.info(f"Deleted session: {session_id}")
            
            return JSONResponse({
                "status": "deleted",
                "session_id": session_id
            })
        else:
            return JSONResponse({
                "error": "Session not found"
            }, status_code=404)
            
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return JSONResponse({
            "error": format_error_message(e)
        }, status_code=500)


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "create_session":
                # Create new session
                session_id = str(uuid.uuid4())
                
                if DEMO_MODE:
                    agent = await create_mock_agent()
                else:
                    agent = HelloWorldAgent()
                    await agent.create_agent()
                
                thread = await agent.create_thread()
                
                active_agents[session_id] = agent
                active_sessions[session_id] = thread.id
                
                await websocket.send_json({
                    "type": "session_created",
                    "session_id": session_id,
                    "thread_id": thread.id,
                    "mode": "demo" if DEMO_MODE else "azure"
                })
                
            elif action == "send_message":
                message = data.get("message", "").strip()
                session_id = data.get("session_id")
                
                if not session_id or session_id not in active_agents:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid session"
                    })
                    continue
                
                if not message:
                    await websocket.send_json({
                        "type": "error", 
                        "message": "Message cannot be empty"
                    })
                    continue
                
                # Send typing indicator
                await websocket.send_json({
                    "type": "typing",
                    "message": "Agent is thinking..."
                })
                
                # Get agent response
                agent = active_agents[session_id]
                thread_id = active_sessions[session_id]
                responses = await agent.run_conversation(thread_id, message)
                
                # Send response
                await websocket.send_json({
                    "type": "message",
                    "responses": responses,
                    "session_id": session_id
                })
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": format_error_message(e)
        })
    finally:
        # Cleanup session if it exists
        if session_id and session_id in active_agents:
            try:
                agent = active_agents[session_id]
                await agent.cleanup_agent()
                del active_agents[session_id]
                del active_sessions[session_id]
                logger.info(f"Cleaned up WebSocket session: {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up WebSocket session: {e}")


# Define routes
routes = [
    Route("/", homepage),
    Route("/health", health_check),
    Route("/api/session", create_session, methods=["POST"]),
    Route("/api/message", send_message, methods=["POST"]),
    Route("/api/session/delete", delete_session, methods=["POST"]),
    WebSocketRoute("/ws", websocket_endpoint),
]

# Middleware
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

# Create the Starlette application
app = Starlette(debug=True, routes=routes, middleware=middleware)

# Mount static files (if directory exists)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    logger.warning("Static directory not found, skipping static file mounting")


async def startup():
    """Application startup event."""
    logger.info("🚀 Hello World Azure AI Foundry Agent - Starlette App Starting...")
    
    if DEMO_MODE:
        logger.info("🧪 Running in DEMO MODE - no Azure credentials required")
        logger.info("✅ Demo mode ready")
    else:
        # Validate environment in Azure mode
        env_check = validate_environment()
        if not env_check["valid"]:
            logger.error("❌ Environment validation failed:")
            for var in env_check["missing_vars"]:
                logger.error(f"   Missing: {var}")
            raise ValueError("Missing required environment variables")
        
        if env_check["warnings"]:
            for warning in env_check["warnings"]:
                logger.warning(f"⚠️  {warning}")
        
        logger.info("✅ Environment validation passed")
    
    logger.info("🌐 Server ready at http://localhost:8000")


async def shutdown():
    """Application shutdown event."""
    logger.info("🧹 Cleaning up active sessions...")
    
    # Cleanup all active agents
    for session_id, agent in list(active_agents.items()):
        try:
            await agent.cleanup_agent()
            logger.info(f"Cleaned up session: {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    active_agents.clear()
    active_sessions.clear()
    logger.info("👋 Shutdown complete")


# Add event handlers
app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the Starlette server."""
    uvicorn.run(
        "web_app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server(reload=True)
