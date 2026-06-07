package agents

import (
	"context"
	"fmt"
	"iter"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/log"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/runner"
	"google.golang.org/adk/server/adka2a/v2"
	"google.golang.org/adk/session"
	"google.golang.org/genai"
)

func newExecutorFrom(a agent.Agent) a2asrv.AgentExecutor {
	return adka2a.NewExecutor(adka2a.ExecutorConfig{
		RunnerConfig: runner.Config{Agent: a, AppName: a.Name(), SessionService: session.InMemoryService()},
		RunConfig:    agent.RunConfig{StreamingMode: agent.StreamingModeSSE},
		BeforeExecuteCallback: func(ctx context.Context, reqCtx *a2asrv.ExecutorContext) (context.Context, error) {
			log.Info(ctx, "agent invoked", "name", a.Name())
			return ctx, nil
		},
		AfterEventCallback: func(ctx adka2a.ExecutorContext, event *session.Event, processed *a2a.TaskArtifactUpdateEvent) error {
			if processed.LastChunk && len(ctx.RequestContext().Message.Parts) > 0 {
				description := fmt.Sprintf("Research results: %q", ctx.RequestContext().Message.Parts[0].Text())
				processed.Artifact.Description = description
			}
			return nil
		},
		AfterExecuteCallback: func(ctx adka2a.ExecutorContext, finalEvent *a2a.TaskStatusUpdateEvent, err error) error {
			log.Info(ctx, "agent finished", "name", a.Name(), "status", finalEvent.Status.State)
			return nil
		},
		GenAIPartConverter: func(ctx context.Context, adkEvent *session.Event, part *genai.Part) (*a2a.Part, error) {
			if part.Text == "" || part.Thought { // only expose text outputs
				return nil, nil
			}
			return adka2a.ToA2APart(part, adkEvent.LongRunningToolIDs)
		},
	})
}

// TaskLoader loads completed tasks by their IDs. Used to inject referenced task content into agent prompts.
type TaskLoader interface {
	Load(context.Context, []a2a.TaskID) ([]*a2a.Task, error)
}

type referencedTaskLoader struct {
	a2asrv.AgentExecutor
	loader TaskLoader
}

// Execute implements [a2asrv.AgentExecutor.Execute]. It preloads referenced tasks and add the data
// to [a2a.Message] contents before delegating to the actual [a2asrv.AgentExecutor].
func (e *referencedTaskLoader) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		log.Info(ctx, "task loader", "tasks", len(execCtx.Message.ReferenceTasks))

		tasks, err := e.loader.Load(ctx, execCtx.Message.ReferenceTasks)
		if err != nil {
			yield(nil, err)
			return
		}
		for _, task := range tasks {
			for _, artifact := range task.Artifacts {
				execCtx.Message.Parts = append(execCtx.Message.Parts, a2a.NewTextPart(artifact.Description+":\n"))
				for _, part := range artifact.Parts {
					execCtx.Message.Parts = append(execCtx.Message.Parts, part)
				}
			}
		}
		for ev, err := range e.AgentExecutor.Execute(ctx, execCtx) {
			if !yield(ev, err) {
				break
			}
		}
	}
}
