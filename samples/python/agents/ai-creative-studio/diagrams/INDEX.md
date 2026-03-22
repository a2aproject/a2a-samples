# Diagrams Quick Reference

> Visual architecture diagrams for the AI Creative Studio multi-agent system

## 🎯 Quick Navigation

### By Topic

**System Overview**
- [`01-system-architecture.mmd`](01-system-architecture.mmd) - Hub-and-spoke architecture

**Workflows**
- [`02-agent-workflow.mmd`](02-agent-workflow.mmd) - Complete campaign sequence
- [`11-planning-first-pattern.mmd`](11-planning-first-pattern.mmd) - Orchestration decision flow

**A2A Protocol**
- [`04-a2a-protocol-flow.mmd`](04-a2a-protocol-flow.mmd) - A2A communication sequence
- [`08-local-vs-cloud-config.mmd`](08-local-vs-cloud-config.mmd) - ⭐ **KEY INNOVATION** - Dual configuration

**Orchestration**
- [`05-agenttool-pattern.mmd`](05-agenttool-pattern.mmd) - AgentTool pattern
- [`06-context-compaction.mmd`](06-context-compaction.mmd) - Context management

**Integration**
- [`07-mcp-integration.mmd`](07-mcp-integration.mmd) - Notion MCP integration

**Deployment**
- [`03-deployment-architecture.mmd`](03-deployment-architecture.mmd) - Cloud infrastructure
- [`09-deployment-process.mmd`](09-deployment-process.mmd) - Parallel deployment

**Observability**
- [`10-observability-logging.mmd`](10-observability-logging.mmd) - Logging architecture

---

## 📖 By Article Series

### Article 1: Introduction to Multi-Agent Systems
- `01-system-architecture.mmd`
- `02-agent-workflow.mmd`

### Article 2: Building Your First ADK Agent
- (Code-focused, minimal diagrams needed)

### Article 3: A2A Protocol Deep Dive
- `04-a2a-protocol-flow.mmd`
- `08-local-vs-cloud-config.mmd` ⭐ **Most important!**

### Article 4: Building the Orchestrator
- `05-agenttool-pattern.mmd`
- `11-planning-first-pattern.mmd`
- `02-agent-workflow.mmd` (reference)

### Article 5: Context Compaction
- `06-context-compaction.mmd`

### Article 6: MCP Integration
- `07-mcp-integration.mmd`

### Article 7: Deployment
- `03-deployment-architecture.mmd`
- `09-deployment-process.mmd`

### Article 8: Observability
- `10-observability-logging.mmd`

---

## 🌟 Key Innovation Diagrams

These diagrams highlight your unique contributions:

1. **`08-local-vs-cloud-config.mmd`** ⭐⭐⭐
   - Most important innovation
   - Dual configuration pattern
   - Makes A2A work in both environments

2. **`09-deployment-process.mmd`** ⭐⭐
   - Parallel deployment (3x faster)
   - asyncio.gather approach

3. **`06-context-compaction.mmd`** ⭐⭐
   - Lazy compaction solution
   - Scales to 10+ agents

4. **`05-agenttool-pattern.mmd`** ⭐
   - LLM-driven flexible routing
   - AgentTool wrapper pattern

5. **`07-mcp-integration.mmd`** ⭐
   - Dynamic schema discovery
   - Multilingual Notion support

---

## 📊 Diagram Types

### System Architecture (Static)
- `01-system-architecture.mmd`
- `03-deployment-architecture.mmd`
- `05-agenttool-pattern.mmd`
- `08-local-vs-cloud-config.mmd`
- `10-observability-logging.mmd`

### Sequence Flows (Dynamic)
- `02-agent-workflow.mmd`
- `04-a2a-protocol-flow.mmd`
- `07-mcp-integration.mmd`

### Process Flows (Steps)
- `06-context-compaction.mmd`
- `09-deployment-process.mmd`

### State Machines (Logic)
- `11-planning-first-pattern.mmd`

---

## 🎨 Color Legend

All diagrams use consistent Google-inspired colors:

| Color | Hex | Usage |
|-------|-----|-------|
| 🔵 Blue | `#4285f4` | Orchestrator, tools, innovations |
| 🟢 Green | `#34a853` | Specialist agents, success |
| 🟡 Yellow | `#fbbc04` | Gemini API, triggers, warnings |
| 🔴 Red | `#ea4335` | User interface, errors, challenges |
| ⚪ Gray | `#9aa0a6` | Remote agents, infrastructure |

---

## 🚀 Quick Start

### View Online
1. Copy any `.mmd` file content
2. Go to [Mermaid Live](https://mermaid.live/)
3. Paste and preview

### Use in Articles
````markdown
```mermaid
# ... paste diagram content ...
```
````

### Export as Image
1. Open in Mermaid Live
2. Click "Actions" → "PNG" or "SVG"
3. Use in presentations or Medium articles

---

## 📝 Diagram Statistics

- **Total Diagrams**: 11
- **System Architecture**: 3
- **Sequence Diagrams**: 3
- **Flow Charts**: 4
- **State Diagrams**: 1

**Lines of Mermaid Code**: ~800 lines
**Estimated Rendering Time**: ~30 seconds for all diagrams

---

## 🔗 Related Resources

- [README.md](README.md) - Detailed diagram descriptions
- [ARTICLE_SERIES_PLAN.md](../ARTICLE_SERIES_PLAN.md) - Article series structure
- [Mermaid Documentation](https://mermaid.js.org/intro/) - Mermaid syntax reference

---

**Created**: December 2024
**Last Updated**: December 2024
**Maintainer**: AI Creative Studio Team
