# Declarative UI Extension

This directory contains an example of what an extension specification looks
like. This extension allows an agent to send declarative UI structures,
based on the Particle/SUIP specification, to a client. The purpose is to show:

- How extension specifications can describe the extension protocol
- How extensions are exposed in AgentCards
- How extensions are activated in the request/response flow
- How `DataPart` can be used to send rich, structured data.
- How extension libraries can be implemented in a composable, standalone style
- How extensions can be versioned by including the version in the URI

The v1 directory contains the specification document. A library implementation
in Python is present in `samples/python/extensions/declarative-ui`. The multi-agent
host has been updated to add support for this extension.
