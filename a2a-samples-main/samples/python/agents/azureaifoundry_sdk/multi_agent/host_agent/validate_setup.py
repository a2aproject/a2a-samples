#!/usr/bin/env python3
"""
Setup validation script for Azure AI Routing Agent.

This script checks that all required dependencies and configuration
are properly set up before running the main application.
"""

import os
import sys
from typing import List, Tuple


def check_environment_variables() -> Tuple[bool, List[str]]:
    """Check if required environment variables are set."""
    required_vars = [
        "AZURE_AI_FOUNDRY_PROJECT_ENDPOINT",
        "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def check_optional_variables() -> List[str]:
    """Check optional environment variables."""
    optional_vars = [
        "TOOL_AGENT_URL",
        "PLAYWRIGHT_AGENT_URL"
    ]
    
    missing_vars = []
    for var in optional_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars


def check_python_version() -> bool:
    """Check if Python version meets requirements."""
    return sys.version_info >= (3, 13)


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if required packages are installed."""
    required_packages = [
        "azure.ai.agents",
        "azure.identity", 
        "gradio",
        "httpx",
        "dotenv"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages


def main():
    """Run all validation checks."""
    print("🔍 Azure AI Routing Agent - Setup Validation")
    print("=" * 50)
    
    all_checks_passed = True
    
    # Check Python version
    print("\n📦 Python Version Check:")
    if check_python_version():
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} (Required: 3.13+)")
    else:
        print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} (Required: 3.13+)")
        all_checks_passed = False
    
    # Check dependencies
    print("\n📚 Dependencies Check:")
    deps_ok, missing_deps = check_dependencies()
    if deps_ok:
        print("✅ All required packages are installed")
    else:
        print(f"❌ Missing packages: {', '.join(missing_deps)}")
        print("   Run: uv install or pip install -r requirements.txt")
        all_checks_passed = False
    
    # Check environment variables
    print("\n🔧 Environment Variables Check:")
    env_ok, missing_env = check_environment_variables()
    if env_ok:
        print("✅ All required environment variables are set")
    else:
        print(f"❌ Missing required variables: {', '.join(missing_env)}")
        print("   Copy .env.template to .env and configure the values")
        all_checks_passed = False
    
    # Check optional variables
    missing_optional = check_optional_variables()
    if missing_optional:
        print(f"⚠️  Optional variables not set: {', '.join(missing_optional)}")
        print("   These will use default values")
    
    # Display current configuration
    print("\n📊 Current Configuration:")
    config_vars = [
        "AZURE_AI_FOUNDRY_PROJECT_ENDPOINT",
        "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", 
        "TOOL_AGENT_URL",
        "PLAYWRIGHT_AGENT_URL"
    ]
    
    for var in config_vars:
        value = os.getenv(var, "Not set")
        # Mask sensitive information
        if "endpoint" in var.lower() and value != "Not set":
            value = value[:20] + "..." if len(value) > 20 else value
        print(f"   {var}: {value}")
    
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 All checks passed! You're ready to run the application.")
        print("   Run: python '__main__ .py'")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
