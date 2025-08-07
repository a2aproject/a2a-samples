#!/usr/bin/env python3
"""CLI commands for the Hello World Azure AI Foundry Agent."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from .web_app import run_server
from .hello_agent import demo_interaction
from .utils import validate_environment, print_banner, get_system_info


def cmd_web(args):
    """Run the web server."""
    print_banner()
    print("🌐 Starting web server...")
    
    env_check = validate_environment()
    if not env_check["valid"]:
        print("❌ Environment validation failed:")
        for var in env_check["missing_vars"]:
            print(f"   Missing: {var}")
        return 1
    
    print(f"📱 Server will be available at: http://localhost:{args.port}")
    print("🛑 Press Ctrl+C to stop the server")
    
    try:
        run_server(
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


async def cmd_console(args):
    """Run the console demo."""
    print_banner()
    print("💬 Starting console demo...")
    
    env_check = validate_environment()
    if not env_check["valid"]:
        print("❌ Environment validation failed:")
        for var in env_check["missing_vars"]:
            print(f"   Missing: {var}")
        return 1
    
    try:
        await demo_interaction()
    except KeyboardInterrupt:
        print("\n👋 Demo stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


def cmd_check(args):
    """Check environment and system information."""
    print_banner()
    print("🔍 Environment Check")
    print("=" * 40)
    
    # Environment validation
    env_check = validate_environment()
    
    if env_check["valid"]:
        print("✅ Environment validation: PASSED")
    else:
        print("❌ Environment validation: FAILED")
        print("\nMissing variables:")
        for var in env_check["missing_vars"]:
            print(f"   - {var}")
    
    if env_check["warnings"]:
        print("\n⚠️  Warnings:")
        for warning in env_check["warnings"]:
            print(f"   - {warning}")
    
    # System information
    if args.verbose:
        print("\n📋 System Information")
        print("-" * 25)
        sys_info = get_system_info()
        for key, value in sys_info.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
    
    return 0 if env_check["valid"] else 1


def cmd_info(args):
    """Show application information."""
    print_banner()
    print("📚 Application Information")
    print("=" * 40)
    
    print("🤖 Hello World Azure AI Foundry Agent")
    print("📝 A simple example demonstrating Azure AI Foundry agent capabilities")
    print()
    
    print("Available commands:")
    print("  web      - Start the web interface (default)")
    print("  console  - Run the console demo")
    print("  check    - Check environment and configuration")
    print("  info     - Show this information")
    print()
    
    print("Examples:")
    print("  python cli.py web --port 3000")
    print("  python cli.py console")
    print("  python cli.py check --verbose")
    print()
    
    print("Environment variables required:")
    print("  AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
    print("  AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Hello World Azure AI Foundry Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Web command
    web_parser = subparsers.add_parser("web", help="Start the web server")
    web_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    web_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    web_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    web_parser.set_defaults(func=cmd_web)
    
    # Console command
    console_parser = subparsers.add_parser("console", help="Run console demo")
    console_parser.set_defaults(func=lambda args: asyncio.run(cmd_console(args)))
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check environment")
    check_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information")
    check_parser.set_defaults(func=cmd_check)
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show application information")
    info_parser.set_defaults(func=cmd_info)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Default to web if no command specified
    if not args.command:
        args.command = "web"
        args.host = "0.0.0.0"
        args.port = 8000
        args.reload = False
        args.func = cmd_web
    
    # Run the command
    try:
        exit_code = args.func(args)
        sys.exit(exit_code or 0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
