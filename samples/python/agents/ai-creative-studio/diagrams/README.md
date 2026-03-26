# Architecture Diagrams

This directory contains Mermaid diagrams illustrating the architecture and key innovations of the AI Creative Studio multi-agent system.

## Diagram Overview

| Diagram | Description | Use in Article |
| --------- | ------------- | ---------------- |
| `01-system-architecture.mmd` | Overall hub-and-spoke architecture | Article 1: Introduction |
| `02-agent-workflow.mmd` | Complete campaign sequence flow | Article 1, 4: Workflow overview |
| `03-deployment-architecture.mmd` | Cloud infrastructure deployment | Article 7: Deployment |
| `04-a2a-protocol-flow.mmd` | A2A communication sequence | Article 3: A2A Protocol |
| `05-agenttool-pattern.mmd` | AgentTool pattern and LLM-driven routing | Article 4: Orchestrator |
| `06-context-compaction.mmd` | Lazy context compaction workflow | Article 5: Scaling |
| `07-mcp-integration.mmd` | Notion MCP integration with dynamic schema | Article 6: MCP Integration |
| `08-local-vs-cloud-config.mmd` | Dual configuration pattern (KEY INNOVATION) | Article 3: A2A Protocol |
| `09-deployment-process.mmd` | Parallel deployment flow | Article 7: Deployment |
| `10-observability-logging.mmd` | Logging and monitoring architecture | Article 8: Observability |
| `11-planning-first-pattern.mmd` | Planning-first orchestration pattern | Article 4: Orchestrator |

## How to Use These Diagrams

### In Markdown/Medium Articles

Simply copy the content of any `.mmd` file and paste it into a Markdown code block with the `mermaid` language tag:

```mermaid
graph TB
    # ... diagram content ...
```

### In Mermaid Live Editor

1. Go to [Mermaid Live Editor](https://mermaid.live/)
2. Copy the content of any `.mmd` file
3. Paste into the editor
4. Export as PNG/SVG for presentations

### In GitHub

GitHub automatically renders Mermaid diagrams in Markdown files. Just use:

```mermaid
# ... diagram content ...
```

### In VS Code

Install the [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) extension to preview diagrams inline.

## Diagram Details

### 01. System Architecture
**Purpose**: Shows the overall hub-and-spoke model with 1 orchestrator and 5 specialist agents.

**Key Elements**:
- Creative Director (Vertex AI Agent Engine)
- 5 specialist agents (Cloud Run)
- External services (Google Search, Notion, Gemini)
- A2A protocol communication

**Best for**: High-level system overview

---

### 02. Agent Workflow
**Purpose**: Illustrates the complete campaign creation sequence with all 5 agents.

**Key Elements**:
- Planning phase
- Sequential execution
- Context passing between agents
- Verification at each step

**Best for**: Understanding the end-to-end workflow

---

### 03. Deployment Architecture
**Purpose**: Shows cloud infrastructure and deployment targets.

**Key Elements**:
- Vertex AI Agent Engine for orchestrator
- Cloud Run services for specialists
- Environment variable configuration
- Auto-scaling setup

**Best for**: Understanding production deployment

---

### 04. A2A Protocol Flow
**Purpose**: Details the Agent-to-Agent communication protocol.

**Key Elements**:
- JSONRPC message format
- RemoteA2aAgent client
- A2A Server handling
- Request/response flow

**Best for**: Understanding A2A protocol mechanics

---

### 05. AgentTool Pattern
**Purpose**: Explains how remote agents are wrapped as tools for flexible orchestration.

**Key Elements**:
- LLM-driven routing
- AgentTool wrappers
- RemoteA2aAgent connections
- Function calling interface

**Best for**: Understanding orchestration flexibility

---

### 06. Context Compaction
**Purpose**: Shows how lazy context compaction solves token limit problems.

**Key Elements**:
- Compaction trigger (after 3 agents)
- Summarization process
- Context preservation strategy
- Token usage optimization

**Best for**: Understanding scalability solution

---

### 07. MCP Integration
**Purpose**: Illustrates Notion integration via Model Context Protocol.

**Key Elements**:
- Dynamic schema discovery
- MCP toolset connection
- npx process management
- Two-database architecture

**Best for**: Understanding external tool integration

---

### 08. Local vs Cloud Run Config ⭐
**Purpose**: **KEY INNOVATION** - Shows dual configuration pattern for local/cloud deployment.

**Key Elements**:
- Listening configuration (HOST/PORT)
- Public configuration (PUBLIC_HOST/PORT/PROTOCOL)
- Environment-based setup
- Agent card URL configuration

**Best for**: Understanding the main A2A deployment innovation

**This is the most important diagram for explaining your unique contribution!**

---

### 09. Deployment Process
**Purpose**: Shows parallel deployment innovation for faster deployment.

**Key Elements**:
- Parallel vs sequential comparison
- asyncio.gather usage
- URL collection
- A2A configuration update

**Best for**: Understanding deployment efficiency

---

### 10. Observability & Logging
**Purpose**: Comprehensive logging and monitoring architecture.

**Key Elements**:
- A2A protocol logging
- ADK built-in logging
- Custom plugins
- Analysis tools (A2A Inspector)

**Best for**: Understanding production monitoring

---

### 11. Planning-First Pattern
**Purpose**: State diagram showing the orchestration decision-making process.

**Key Elements**:
- Analysis phase (complexity detection)
- Planning phase (create execution plan)
- Execution phase (sequential with verification)
- Verification rules

**Best for**: Understanding orchestrator intelligence

---

## Color Coding

Diagrams use consistent Google-inspired colors:

- 🔵 **Blue (#4285f4)**: Orchestrator, tools, innovation highlights
- 🟢 **Green (#34a853)**: Specialist agents, success states
- 🟡 **Yellow (#fbbc04)**: Gemini API, warning states, triggers
- 🔴 **Red (#ea4335)**: User interface, errors, challenges

---

## Diagram Style Guide

### Graph Types Used

- **`graph TB`** (Top to Bottom): System architecture, deployment
- **`sequenceDiagram`**: Workflows, communication flows
- **`stateDiagram-v2`**: State machines, decision flows

### Common Patterns

```mermaid
# Subgraphs for logical grouping
subgraph "Layer Name"
    COMPONENT[Component Name]
end

# Styling for emphasis
style COMPONENT fill:#4285f4,color:#fff,stroke:#333,stroke-width:3px

# Notes for additional context
Note over Component: Explanation text
```

---

## Exporting Diagrams

### For Medium Articles
Medium doesn't support Mermaid natively. Export as PNG:

1. Open in [Mermaid Live](https://mermaid.live/)
2. Click "Actions" → "PNG"
3. Upload to Medium

### For GitHub README
Just embed directly:

```mermaid
# diagram content
```

### For Presentations
Export as SVG for scalable graphics:

1. Mermaid Live → "Actions" → "SVG"
2. Import into PowerPoint/Google Slides

---

## Contributing

When adding new diagrams:

1. Use consistent color scheme (Google colors)
2. Add comments with `%%` for context
3. Update this README with diagram description
4. Test rendering in Mermaid Live
5. Use clear, concise labels

---

## License

These diagrams are part of the AI Creative Studio project and follow the same license.

---

## Questions?

For questions about specific diagrams or how to use them in your articles, refer to:
- [ARTICLE_SERIES_PLAN.md](../ARTICLE_SERIES_PLAN.md) - Article series structure
- [README.md](../README.md) - Project overview
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - Deployment details
