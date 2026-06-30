package main

import (
	"context"
	"fmt"
	"iter"
	"log"

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

		msg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("Verify me!"))
		yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCompleted, msg), nil)
	}
}

func (e *SignedAgentExecutor) Cancel(_ context.Context, _ *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		log.Println("Cancel not supported.")
		yield(nil, fmt.Errorf("cancel is not supported"))
	}
}
