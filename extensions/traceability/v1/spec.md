# Traceability Extension

## Overview

This extension defines how to add traceability information to `Message` and `Artifact`
objects.

## Extension URI

The URI of this extension is `https://github.com/a2aproject/a2a-samples/extensions/traceability/v1`.

This is the only URI accepted for this extension.

## Traceability Format



## Message/Artifact Metadata Field

Traceability information MUST be stored in the metadata for a Message or Artifact, under a
field with the key `github.com/a2aproject/a2a-samples/extensions/traceability/v1/traceability`,
or an addtional artifact in the returned completed response.

```proto
// A Trace message that contains a collection of spans.
message ResponseTrace {
 // A unique identifier for the trace.
 string trace_id = 1;


 // The list of steps that make up this trace.
 repeated Step steps = 2;
}


enum CallTypeEnum {
 AGENT = 1;
 TOOL = 2;
}


message StepAction {
 oneof action {
   ToolInvocation tool_invocation = 1;
   AgentInvocation agent_invocation = 2;
 }
}


message ToolInvocation {
 string tool_name = 1;
 google.protobuf.Struct parameters = 2;
}


message AgentInvocation {
 // The URL of the agent that was invoked.
 string agent_url = 1;
 // the agent name
 string agent_name = 2;
 // The request message sent to the agent.
 google.protobuf.Struct requests = 3;
 // intenral response trace for this specific steps, if the callee also
 // supports the traceability extension and the caller requests traceability.
 ResponseTrace response_trace = 4;
}


// A Step message that represents a single operation within a trace.
message Step {
 // A unique identifier for this step.
 string step_id = 1;


 // The trace_id of the trace this step belongs to.
 string trace_id = 2;


 // The step_id of the parent step. Empty if this is a root step.
 string parent_step_id = 3;


 // The type of the operation this step represents.
 CallTypeEnum call_type = 4;


 // Detailed invocation about the step
 StepAction step_action = 5;


 // The cost of the operation this step represents.
 int64 cost = 6;


 // The token of the operation this step represents.
 int64 total_tokens = 7;


 // A set of key-value attributes with additional details about the step.
 map<string, string> additional_attributes = 8;


 // The latency of the operation this step represents.
 int64 latency = 9;


 // The start time of the operation.
 google.protobuf.Timestamp start_time = 10;


 // The end time of the operation.
 google.protobuf.Timestamp end_time = 11;
}

```

## Extension Activation

Clients indicate their desire to receive traceability on response by specifying
the [Extension URI](#extension-uri) via the transport-defined extension
activation mechanism. For JSON-RPC and HTTP transports, this is indicated via
the `X-A2A-Extensions` HTTP header. For gRPC, this is indicated via the
`X-A2A-Extensions` metadata value.
