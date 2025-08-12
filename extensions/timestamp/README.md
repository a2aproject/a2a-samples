# Hello World Extension

This directory contains an example of what an extension specification looks
like. The extension itself is extremely simple: adding timestamps in the
`metadata` field of `Message` and `Artifact` objects. The purpose is to show:

- How extension specifications can describe the extension protocol
- How extensions are exposed in AgentCards
- How extensions are activated in the request/response flow
- How extensions can be used to augment base A2A types
- How extension libraries can be implemented in a composable, standalone style
- How extensions can be versioned by including the version in the URI

The v1 directory contains the specification document. A library implementation
in Python is present in samples/python/extensions/timestamp. The reimbursement
agent and the demo UI have both been updated to add support for this extension.
