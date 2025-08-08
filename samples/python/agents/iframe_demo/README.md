# Iframe Demo Agent

This agent demonstrates iframe embedded UI component support in the A2A protocol. It shows how agents can embed various types of web content including charts, dashboards, forms, and other interactive elements directly in conversations.

## Features

The agent supports embedding:
- **Charts and Visualizations** - Interactive charts and graphs
- **Dashboards** - Business intelligence dashboards
- **Forms** - Web forms for data collection
- **Custom Web Content** - Any web URL as an embedded iframe

## Usage

### Starting the Agent

```bash
cd samples/python/agents/iframe_demo
uv run .
```

The agent will start on port 10002 by default.

### Adding to Demo UI

1. Start the demo UI: `cd demo/ui && uv run main.py`
2. Go to the "Remote Agents" tab
3. Add agent address: `localhost:10002`
4. Start chatting!

### Example Requests

Try these messages in the demo UI:

- **"Show me a chart"** - Displays a sample visualization
- **"Show me a dashboard"** - Shows an interactive dashboard
- **"Show me a form"** - Embeds a web form
- **"Embed https://example.com"** - Embeds any web URL

## Implementation Details

### Iframe Part Structure

The agent creates iframe components using `DataPart` with the following structure:

```python
iframe_config = {
    "src": "https://example.com/widget",
    "width": "100%",
    "height": "400px", 
    "title": "Embedded Content",
    "sandbox": "allow-scripts allow-same-origin allow-forms",
    "allow": "accelerometer; autoplay; camera; encrypted-media; gyroscope; picture-in-picture"
}
```

### Security Features

The implementation includes several security measures:

- **Sandbox attributes** - Restricts iframe capabilities
- **Permission policies** - Controls what features the iframe can use
- **URL validation** - Ensures only valid URLs are embedded
- **CSP compliance** - Works within Content Security Policy restrictions

### Content Detection

The demo UI detects iframe content by:
1. Checking for `media_type` of `"application/iframe"`
2. Looking for `"src"` field in data parts
3. Using media type `"iframe"` for backwards compatibility

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Request  │    │  Iframe Demo     │    │   Demo UI       │
│   "Show chart"  │───▶│     Agent        │───▶│   Renders       │
│                 │    │                  │    │   Iframe        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  A2A DataPart    │
                       │  with iframe     │
                       │  configuration   │
                       └──────────────────┘
```

## Testing

The agent includes sample iframe configurations for testing:

- Charts from Tableau Public
- Dashboards from various BI tools  
- Forms from Google Forms (example)
- Custom URL embedding

Replace the example URLs with real services for production use.