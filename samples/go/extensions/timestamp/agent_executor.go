package main

import (
	"context"
	"fmt"
	"iter"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

type echoAgent struct{}

func (a *echoAgent) Invoke(ctx context.Context, userRequest string) (string, error) {
	if userRequest != "" {
		return fmt.Sprintf("hello! (%s)", userRequest), nil
	}
	return "hello!", nil
}

type echoExecutor struct {
	agent *echoAgent
}

var _ a2asrv.AgentExecutor = (*echoExecutor)(nil)

func newEchoExecutor() *echoExecutor {
	return &echoExecutor{
		agent: &echoAgent{},
	}
}

func (e *echoExecutor) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		if execCtx.StoredTask == nil {
			task := a2a.NewSubmittedTask(execCtx, execCtx.Message)
			if !yield(task, nil) {
				return
			}
		}

		statusMsg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("working..."))
		statusUpdate := a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateWorking, statusMsg)
		if !yield(statusUpdate, nil) {
			return
		}

		var query string
		if execCtx.Message != nil {
			for _, part := range execCtx.Message.Parts {
				if text := part.Text(); text != "" {
					query = text
					break
				}
			}
		}

		result, err := e.agent.Invoke(ctx, query)
		if err != nil {
			result = fmt.Sprintf("error: %v", err)
		}

		artEvent := a2a.NewArtifactEvent(execCtx, a2a.NewTextPart(result))
		artEvent.Artifact.Name = "result"
		if !yield(artEvent, nil) {
			return
		}

		completedUpdate := a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCompleted, nil)
		if !yield(completedUpdate, nil) {
			return
		}
	}
}

func (e *echoExecutor) Cancel(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {}
}
