package main

import (
	"context"
	"fmt"
	"iter"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2asrv"
)

type SignedAgentExecutor struct{}

func NewSignedAgentExecutor() *SignedAgentExecutor {
	return &SignedAgentExecutor{}
}

func (e *SignedAgentExecutor) Execute(_ context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		if execCtx.StoredTask == nil {
			if !yield(a2a.NewSubmittedTask(execCtx, execCtx.Message), nil) {
				return
			}
		}

		workingMsg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("Processing verification request..."))
		if !yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateWorking, workingMsg), nil) {
			return
		}

		var query string
		if execCtx.Message != nil {
			for _, part := range execCtx.Message.Parts {
				if t := part.Text(); t != "" {
					query = t
					break
				}
			}
		}

		result := "Verify me!"
		if query != "" {
			result = fmt.Sprintf("Verify me! (%s)", query)
		}

		artifactPart := a2a.NewTextPart(result)
		artifactPart.MediaType = "text/plain"
		if !yield(a2a.NewArtifactEvent(execCtx, artifactPart), nil) {
			return
		}

		completedMsg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("Request is completed!"))
		yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCompleted, completedMsg), nil)
	}
}

func (e *SignedAgentExecutor) Cancel(_ context.Context, _ *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		yield(nil, fmt.Errorf("cancel is not supported"))
	}
}

