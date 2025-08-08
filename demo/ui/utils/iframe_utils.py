"""Utility functions for creating iframe embedded UI components in A2A messages."""

import json
from typing import Dict, Any, Optional
from a2a.types import DataPart, Part


def create_iframe_part(
    src: str,
    width: str = "100%",
    height: str = "400px",
    title: str = "Embedded Content",
    sandbox: str = "allow-scripts allow-same-origin allow-forms",
    allow: str = "accelerometer; autoplay; camera; encrypted-media; gyroscope; picture-in-picture",
    **kwargs
) -> Part:
    """
    Create an A2A Part containing an iframe embedded UI component.
    
    Args:
        src: URL of the content to embed in the iframe
        width: Width of the iframe (default: "100%")
        height: Height of the iframe (default: "400px")
        title: Title/name for the iframe (default: "Embedded Content")
        sandbox: Sandbox attributes for security (default: "allow-scripts allow-same-origin allow-forms")
        allow: Permission policy attributes (default: accelerometer, autoplay, etc.)
        **kwargs: Additional iframe attributes
        
    Returns:
        A2A Part containing the iframe configuration
        
    Example:
        # Simple iframe with just a URL
        iframe_part = create_iframe_part("https://example.com/chart")
        
        # Customized iframe for a dashboard
        iframe_part = create_iframe_part(
            src="https://dashboard.example.com/widget/123",
            width="800px",
            height="600px",
            title="Sales Dashboard",
            sandbox="allow-scripts allow-same-origin"
        )
    """
    iframe_config = {
        "src": src,
        "width": width,
        "height": height,
        "title": title,
        "sandbox": sandbox,
        "allow": allow,
        **kwargs
    }
    
    return Part(root=DataPart(data=iframe_config, media_type="application/iframe"))


def create_chart_iframe(
    chart_url: str,
    title: str = "Chart",
    width: str = "100%",
    height: str = "500px"
) -> Part:
    """
    Create an iframe part specifically for charts/graphs.
    
    Args:
        chart_url: URL of the chart to display
        title: Title for the chart
        width: Width of the chart iframe
        height: Height of the chart iframe
        
    Returns:
        A2A Part containing the chart iframe configuration
    """
    return create_iframe_part(
        src=chart_url,
        width=width,
        height=height,
        title=title,
        sandbox="allow-scripts allow-same-origin",  # Restrictive for charts
        allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
    )


def create_dashboard_iframe(
    dashboard_url: str,
    title: str = "Dashboard",
    width: str = "100%", 
    height: str = "700px"
) -> Part:
    """
    Create an iframe part specifically for interactive dashboards.
    
    Args:
        dashboard_url: URL of the dashboard to display
        title: Title for the dashboard
        width: Width of the dashboard iframe
        height: Height of the dashboard iframe
        
    Returns:
        A2A Part containing the dashboard iframe configuration
    """
    return create_iframe_part(
        src=dashboard_url,
        width=width,
        height=height,
        title=title,
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups",  # More permissions for dashboards
        allow="accelerometer; autoplay; camera; encrypted-media; gyroscope; picture-in-picture"
    )


def create_form_iframe(
    form_url: str,
    title: str = "Form",
    width: str = "100%",
    height: str = "600px"
) -> Part:
    """
    Create an iframe part specifically for embedded forms.
    
    Args:
        form_url: URL of the form to display
        title: Title for the form
        width: Width of the form iframe
        height: Height of the form iframe
        
    Returns:
        A2A Part containing the form iframe configuration
    """
    return create_iframe_part(
        src=form_url,
        width=width,
        height=height,
        title=title,
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-top-navigation",
        allow="accelerometer; camera; encrypted-media; gyroscope; microphone; picture-in-picture"
    )


def is_iframe_content(content: Any) -> bool:
    """
    Check if content represents iframe configuration.
    
    Args:
        content: Content to check
        
    Returns:
        True if content appears to be iframe configuration
    """
    if isinstance(content, dict) and "src" in content:
        return True
    try:
        data = json.loads(content) if isinstance(content, str) else content
        return isinstance(data, dict) and "src" in data
    except (json.JSONDecodeError, TypeError):
        return False