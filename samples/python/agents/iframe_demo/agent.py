"""Iframe Demo Agent implementation."""

import json
from typing import Any, List

from a2a.types import DataPart, Message, Part, Role, TextPart


class IframeDemoAgent:
    """Agent that demonstrates iframe embedded UI component functionality."""

    def create_iframe_part(
        self,
        src: str,
        width: str = "100%",
        height: str = "400px",
        title: str = "Embedded Content",
        sandbox: str = "allow-scripts allow-same-origin allow-forms",
        allow: str = "accelerometer; autoplay; camera; encrypted-media; gyroscope; picture-in-picture"
    ) -> Part:
        """Create an iframe part for embedding web content."""
        iframe_config = {
            "src": src,
            "width": width,
            "height": height,
            "title": title,
            "sandbox": sandbox,
            "allow": allow
        }
        return Part(root=DataPart(data=iframe_config))

    def handle_chart_request(self) -> List[Part]:
        """Create a sample chart iframe."""
        # Example chart URLs (these are demo URLs, in practice you'd use real chart services)
        chart_urls = [
            "https://public.tableau.com/shared/QJRYQ4P32?:showVizHome=no&:embed=true",
            "https://plotly.com/~PlotBot/5.embed",
            "https://codepen.io/team/amcharts/embed/GRZeNVe?default-tab=result&theme-id=light"
        ]
        
        parts = [
            Part(root=TextPart(text="Here's a sample chart showing sales data:")),
            self.create_iframe_part(
                src=chart_urls[0],
                height="500px",
                title="Sales Dashboard Chart",
                sandbox="allow-scripts allow-same-origin"
            )
        ]
        return parts

    def handle_dashboard_request(self) -> List[Part]:
        """Create a sample dashboard iframe."""
        parts = [
            Part(root=TextPart(text="Here's an interactive dashboard:")),
            self.create_iframe_part(
                src="https://public.tableau.com/views/SuperstoreSample/Overview?:showVizHome=no&:embed=true",
                height="700px",
                title="Business Dashboard",
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            )
        ]
        return parts

    def handle_form_request(self) -> List[Part]:
        """Create a sample form iframe."""
        parts = [
            Part(root=TextPart(text="Here's an embedded form you can fill out:")),
            self.create_iframe_part(
                src="https://forms.gle/example",  # Replace with actual form URL
                height="600px",
                title="Feedback Form",
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-top-navigation"
            )
        ]
        return parts

    def handle_custom_url_request(self, url: str, title: str = None) -> List[Part]:
        """Embed a custom URL as an iframe."""
        if not url.startswith(('http://', 'https://')):
            return [
                Part(root=TextPart(text="Error: Please provide a valid URL starting with http:// or https://"))
            ]
            
        parts = [
            Part(root=TextPart(text=f"Here's the embedded content from {url}:")),
            self.create_iframe_part(
                src=url,
                height="500px",
                title=title or "Embedded Web Content"
            )
        ]
        return parts

    async def generate_response(self, message: str) -> List[Part]:
        """Generate a response with iframe content based on the user's message."""
        message_lower = message.lower()
        
        if "chart" in message_lower or "graph" in message_lower or "visualization" in message_lower:
            return self.handle_chart_request()
            
        elif "dashboard" in message_lower:
            return self.handle_dashboard_request()
            
        elif "form" in message_lower:
            return self.handle_form_request()
            
        elif "embed" in message_lower and ("http" in message_lower):
            # Extract URL from message
            words = message.split()
            url = None
            for word in words:
                if word.startswith(('http://', 'https://')):
                    url = word
                    break
            
            if url:
                return self.handle_custom_url_request(url)
            else:
                return [
                    Part(root=TextPart(text="Please provide a valid URL to embed (starting with http:// or https://)"))
                ]
                
        else:
            # Default response showing capabilities
            return [
                Part(root=TextPart(text="""\
I can help you embed various types of web content using iframes! Here's what I can do:

🔧 **Available Commands:**
- "Show me a chart" - Display a sample chart visualization
- "Show me a dashboard" - Display an interactive dashboard  
- "Show me a form" - Display an embeddable form
- "Embed [URL]" - Embed any web URL as an iframe

🎯 **Examples:**
- "Show me a sales chart"
- "Display the analytics dashboard"
- "Embed https://example.com/widget"

What would you like me to embed for you?""")),
            ]