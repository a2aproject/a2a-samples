package timestamp

import (
	"context"
	"iter"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

// ServerInterceptor implements a2asrv.ExecutorContextInterceptor to timestamp incoming messages.
type ServerInterceptor struct {
	ext *TimestampExtension
}

// NewServerInterceptor creates a new ServerInterceptor.
func NewServerInterceptor(ext *TimestampExtension) *ServerInterceptor {
	return &ServerInterceptor{ext: ext}
}

var _ a2asrv.ExecutorContextInterceptor = (*ServerInterceptor)(nil)

// Intercept implements a2asrv.ExecutorContextInterceptor.
func (s *ServerInterceptor) Intercept(ctx context.Context, execCtx *a2asrv.ExecutorContext) (context.Context, error) {
	if s.ext.IsRequested(ctx) && execCtx.Message != nil {
		s.ext.ApplyTimestamp(execCtx.Message)
	}
	return ctx, nil
}

// WrapExecutor wraps an executor to automatically timestamp outgoing messages and artifacts when requested.
func WrapExecutor(executor a2asrv.AgentExecutor, ext *TimestampExtension) a2asrv.AgentExecutor {
	return &timestampingAgentExecutor{
		delegateAgentExecutor: executor,
		ext:                   ext,
	}
}

type timestampingAgentExecutor struct {
	delegateAgentExecutor a2asrv.AgentExecutor
	ext                   *TimestampExtension
}

var _ a2asrv.AgentExecutor = (*timestampingAgentExecutor)(nil)

func (e *timestampingAgentExecutor) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		requested := e.ext.IsRequested(ctx)
		for event, err := range e.delegateAgentExecutor.Execute(ctx, execCtx) {
			if err != nil {
				yield(nil, err)
				return
			}
			if requested && event != nil {
				e.ext.TimestampEvent(event)
			}
			if !yield(event, nil) {
				return
			}
		}
	}
}

func (e *timestampingAgentExecutor) Cancel(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		requested := e.ext.IsRequested(ctx)
		for event, err := range e.delegateAgentExecutor.Cancel(ctx, execCtx) {
			if err != nil {
				yield(nil, err)
				return
			}
			if requested && event != nil {
				e.ext.TimestampEvent(event)
			}
			if !yield(event, nil) {
				return
			}
		}
	}
}
