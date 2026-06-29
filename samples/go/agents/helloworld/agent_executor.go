package main

import (
	"context"
	"fmt"
	"iter"
	"log"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2asrv"
)

// --8<-- [start:HelloWorldAgent]

// HelloWorldAgent represents the core Hello World Agent.
type HelloWorldAgent struct{}

// Invoke invokes the Hello World agent to generate a response.
func (a *HelloWorldAgent) Invoke(userRequest string) string {
	return fmt.Sprintf("Hello, World! I have received your request (%s)", userRequest)
}

// --8<-- [end:HelloWorldAgent]

// --8<-- [start:HelloWorldAgentExecutor_init]

// HelloWorldAgentExecutor is the test AgentProxy implementation for Go.
type HelloWorldAgentExecutor struct {
	agent *HelloWorldAgent
}

// NewHelloWorldAgentExecutor initializes a new HelloWorldAgentExecutor instance.
func NewHelloWorldAgentExecutor() *HelloWorldAgentExecutor {
	return &HelloWorldAgentExecutor{
		agent: &HelloWorldAgent{},
	}
}

// --8<-- [end:HelloWorldAgentExecutor_init]

// --8<-- [start:HelloWorldAgentExecutor_execute]

// Execute processes the incoming user request.
func (e *HelloWorldAgentExecutor) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		// 1. Collect a task from request context / yield submitted task event if new
		if execCtx.StoredTask == nil {
			if !yield(a2a.NewSubmittedTask(execCtx, execCtx.Message), nil) {
				return
			}
		}

		// 2. Update task status to WORKING
		workingMsg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("Processing request..."))
		if !yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateWorking, workingMsg), nil) {
			return
		}

		// 3. Collect user request from request content and invoke LLM agent to generate content
		var query string
		for _, part := range execCtx.Message.Parts {
			if text := part.Text(); text != "" {
				query = text
				break
			}
		}

		var result string
		if query != "" {
			result = e.agent.Invoke(query)
		} else {
			result = "No text input is provided!"
		}

		// 4. Print result and yield generated response artifact as completed status message
		log.Println("Result: ", result)

		completedMsg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(result))
		yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCompleted, completedMsg), nil)
	}
}

// --8<-- [end:HelloWorldAgentExecutor_execute]

// --8<-- [start:HelloWorldAgentExecutor_cancel]

// Cancel handles task cancellation (not supported in this sample).
func (e *HelloWorldAgentExecutor) Cancel(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		yield(nil, fmt.Errorf("cancel is not supported"))
	}
}

// --8<-- [end:HelloWorldAgentExecutor_cancel]
