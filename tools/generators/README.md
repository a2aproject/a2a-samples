# A2A Agent Card Generator

Interactive Google Colab notebook for generating A2A-compliant Agent Cards through user-friendly forms, making agent card creation accessible to developers without requiring manual JSON editing.

## 🚀 Quick Start

### Standard A2A Agent Card Generator

Generate Agent Cards conforming to the official A2A Protocol specification.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/a2aproject/a2a-samples/blob/main/tools/generators/A2A_Standard_Agent_Card_Generator.ipynb)

**Use this when:** You need a standard-compliant Agent Card for production deployment.

## Features

- ✅ Interactive forms with validation
- ✅ Color-coded sections for easy navigation
- ✅ JSON export with validation
- ✅ Self-contained documentation (embedded in notebook)
- ✅ Example Agent Cards (Recipe, Research, Weather)
- ✅ Follows [A2A Protocol v1.0](https://a2a-protocol.org/latest/specification/) specification
- ✅ Ready for `.well-known/agent-card.json` deployment

## Interactive Sections

- 🔵 **Basic Information** — name, version, description, provider
- 🟢 **Service Endpoints** — JSON-RPC, gRPC, HTTP+JSON bindings
- 🟡 **Capabilities** — streaming, push notifications, history
- 🟣 **Interaction Modes** — input/output media types
- 🔶 **Skills** — capabilities with tags and examples
- 🟪 **JSON Generation** — preview and download

## Usage

1. **Open in Colab** — Click the badge above
2. **Run Setup Cell** — Install dependencies (first cell)
3. **Fill Out Forms** — Complete each colored section
4. **Generate JSON** — Click "Generate JSON" button
5. **Download** — Click "Download JSON" button
6. **Deploy** — Place at `https://yourdomain.com/.well-known/agent-card.json`

## Deployment

Place your generated Agent Card at the standard discovery location:

```
https://yourdomain.com/.well-known/agent-card.json
```

Or serve from any custom URL and share the link directly.

## Examples

See the `examples/` directory for sample Agent Cards:

- [`recipe_assistant_agent_card.json`](examples/recipe_assistant_agent_card.json) — Recipe search and creation agent
- [`research_assistant_agent_card.json`](examples/research_assistant_agent_card.json) — Academic research assistant
- [`weather_agent_card.json`](examples/weather_agent_card.json) — Weather information and forecasts

## Files

```
tools/generators/
├── README.md
├── A2A_Standard_Agent_Card_Generator.ipynb
└── examples/
    ├── recipe_assistant_agent_card.json
    ├── research_assistant_agent_card.json
    └── weather_agent_card.json
```

## Known Limitations

- No support for security schemes yet (OAuth, API keys) — manual addition required
- No support for extensions — add via JSON editing post-generation
- Single interface per addition (no bulk import)

## Testing

- ✅ All cells execute without errors
- ✅ Widgets render and function correctly
- ✅ JSON generation and download working
- ✅ Tested successfully by Gemini (cross-AI validation)

## Author

**Concept & Design:** Paola Di Maio — [Center for Systems, Knowledge Representation and Neuroscience, Ronin Institute](https://ronininstitute.org/)  
**Implementation:** Claude (Anthropic)  
**Affiliation:** Chair, [W3C AI Knowledge Representation Community Group](https://www.w3.org/community/ai-kr/)

## License

Apache License 2.0 — see the [A2A samples repository](https://github.com/a2aproject/a2a-samples) for details.
