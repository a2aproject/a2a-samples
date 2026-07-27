package itest_test

import (
	"context"
	"testing"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/workqueue"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/msgstream"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/testutil"
)

func TestWorkQueue_WriteAndReceive(t *testing.T) {
	testutil.SetupNATS(t)

	_, js := testutil.ConnectNATS(t)

	ctx := context.Background()
	queue, err := msgstream.CreateWorkQueue(ctx, js, domain.AgentResearcher)
	if err != nil {
		t.Fatalf("create work queue: %v", err)
	}

	// Register handler that captures received payloads.
	received := make(chan *workqueue.Payload, 1)
	queue.RegisterHandler(workqueue.HandlerConfig{}, func(_ context.Context, p *workqueue.Payload) (a2a.SendMessageResult, error) {
		received <- p
		return &a2a.Task{ID: p.TaskID}, nil
	})

	// Write a payload.
	taskID := a2a.NewTaskID()
	payload := &workqueue.Payload{
		TaskID: taskID,
		Type:   workqueue.PayloadTypeExecute,
		ExecuteRequest: &a2a.SendMessageRequest{
			Message: a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("test workqueue")),
		},
	}
	if _, err := queue.Write(ctx, payload); err != nil {
		t.Fatalf("write: %v", err)
	}

	// Wait for handler to receive it.
	select {
	case got := <-received:
		if got.TaskID != taskID {
			t.Errorf("task ID: got %s, want %s", got.TaskID, taskID)
		}
		if got.Type != workqueue.PayloadTypeExecute {
			t.Errorf("type: got %s, want %s", got.Type, workqueue.PayloadTypeExecute)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("timeout waiting for handler to receive payload")
	}
}
