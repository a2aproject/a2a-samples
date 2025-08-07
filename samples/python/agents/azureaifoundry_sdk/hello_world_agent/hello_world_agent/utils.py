"""Utilities for the Hello World Azure AI Foundry Agent."""

import logging
import os
from typing import Dict, Any


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_environment() -> Dict[str, Any]:
    """Validate that required environment variables are set.
    
    Returns:
        Dict with validation results
    """
    required_vars = [
        "AZURE_AI_FOUNDRY_PROJECT_ENDPOINT",
        "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
    ]
    
    results = {
        "valid": True,
        "missing_vars": [],
        "warnings": []
    }
    
    for var in required_vars:
        if not os.getenv(var):
            results["valid"] = False
            results["missing_vars"].append(var)
    
    # Check optional variables
    optional_vars = [
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET", 
        "AZURE_TENANT_ID"
    ]
    
    auth_vars_set = sum(1 for var in optional_vars if os.getenv(var))
    if 0 < auth_vars_set < len(optional_vars):
        results["warnings"].append(
            "Some Azure authentication variables are set but not all. "
            "Make sure you have either all three (client ID, secret, tenant ID) "
            "or none (to use default Azure credential)."
        )
    
    return results


def format_error_message(error: Exception) -> str:
    """Format error messages in a user-friendly way.
    
    Args:
        error: The exception to format
        
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Common error types and user-friendly messages
    error_mappings = {
        "ClientAuthenticationError": (
            "Authentication failed. Please check your Azure credentials. "
            "Make sure you're logged in with 'az login' or have set the correct "
            "environment variables."
        ),
        "ResourceNotFoundError": (
            "Resource not found. Please check your Azure AI Foundry project "
            "endpoint and model deployment name."
        ),
        "HttpResponseError": (
            "HTTP error occurred. This might be a temporary issue or a "
            "configuration problem."
        ),
    }
    
    if error_type in error_mappings:
        return f"{error_mappings[error_type]}\n\nOriginal error: {error_msg}"
    
    return f"{error_type}: {error_msg}"


def print_banner() -> None:
    """Print a nice banner for the application."""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║        Hello World Azure AI Foundry Agent                   ║
    ║                                                              ║
    ║        A simple example demonstrating Azure AI Foundry      ║
    ║        agent capabilities with minimal complexity           ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def get_system_info() -> Dict[str, str]:
    """Get system information for debugging.
    
    Returns:
        Dictionary with system information
    """
    import sys
    import platform
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture()[0],
        "machine": platform.machine(),
    }
