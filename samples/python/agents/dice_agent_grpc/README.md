# gRPC agent example

This example setups up an A2AServer that supports gRPC transport for interacting with the Agent.

The example also sets up a HTTP server that serves the public agent card at well-known, which acts as a mechanism for clients to discover agents.

Serving agent card at well-known url is optional and only one of the discovery methods for agents.