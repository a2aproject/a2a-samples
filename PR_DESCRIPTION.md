## Bob's Brain Foreman-Worker Pattern Demo

This sample demonstrates the foreman-worker delegation pattern used in [Bob's Brain](https://github.com/jeremylongshore/bobs-brain), a multi-agent ADK compliance department.

### What This Sample Shows

- **Foreman Agent** - Middle manager that analyzes requests and routes tasks to specialists
- **Worker Agent** - Specialist that performs domain-specific tasks (ADK compliance analysis)
- **AgentCards (A2A 0.3.0)** - Service discovery with skill schemas and SPIFFE identities
- **HTTP-based delegation** - Foreman → Worker communication over REST endpoints

### Demo Scope and Limitations

This sample illustrates core architectural patterns from Bob's Brain, but with important simplifications:

1. **Foreman LLM Usage**: The foreman's `LlmAgent` is instantiated but the current Flask routes call tools directly. A future refactor will route requests through `agent.run()` to let the LLM choose which tools to invoke based on input.

2. **No Bob Orchestrator**: This sample starts at the foreman level. The full Bob's Brain system has Bob (global orchestrator) → Foreman → Workers, with A2A communication between Bob and the foreman.

3. **Single Specialist**: Only one worker is implemented for clarity. Production Bob's Brain has 8 specialized workers (design, issues, fixes, QA, docs, cleanup, indexing).

4. **Deterministic Workers**: The worker uses deterministic Python functions without LLM calls. This is intentional for cost optimization and consistency.

This sample represents how we structure agent departments with clear responsibility separation, not a complete production deployment.

### Production Bob's Brain

For the complete system with 10 agents, dual memory, CI/CD, and full A2A orchestration:
- **Repository**: https://github.com/jeremylongshore/bobs-brain
- **Release**: v0.13.0
- **Quality Score**: 95/100 (145 docs, 65%+ test coverage, 28 canonical standards)

### Running the Demo

See [README.md](./samples/python/agents/bobs_brain_foreman_worker/README.md) for setup and usage instructions.
