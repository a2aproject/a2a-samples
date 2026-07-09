"""Entry point for the Hello World Azure AI Foundry Agent package.

Run this module to start the Starlette web application.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Make sure environment variables are set.")

from .web_app import run_server
from .utils import validate_environment, print_banner


def main() -> None:
    """Main entry point for the Hello World agent web app."""
    print_banner()
    print("🚀 Starting Hello World Azure AI Foundry Agent Web App...")
    
    # Check if we're in development/demo mode
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    
    if not demo_mode:
        # Check required environment variables
        required_vars = [
            "AZURE_AI_FOUNDRY_PROJECT_ENDPOINT",
            "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print("❌ Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            print("\nPlease set these variables in your .env file or environment.")
            print("See .env.template for an example.")
            print("\n💡 To run in demo mode (without Azure connection), set DEMO_MODE=true")
            sys.exit(1)
        
        # Additional validation
        env_check = validate_environment()
        if env_check["warnings"]:
            for warning in env_check["warnings"]:
                print(f"⚠️  {warning}")
        
        print("✅ Environment validation passed")
    else:
        print("🧪 Running in DEMO MODE (no Azure connection required)")
    
    print("🌐 Starting web server...")
    print("📱 Open your browser to: http://localhost:8000")
    print("🛑 Press Ctrl+C to stop the server")
    print()
    
    try:
        # Run the Starlette server
        run_server(host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
