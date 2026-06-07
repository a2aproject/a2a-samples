package cluster

import (
	"context"
	"errors"
	"fmt"
	"sync"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/log"
)

// Client wraps [a2aclient.Client] to simplify app-specific operations.
type Client struct {
	Client *a2aclient.Client
	card   *a2a.AgentCard
}

// CreateClient creates a new [Client] client from the given agent endpoint URL.
func CreateClient(ctx context.Context, endpoint string) (*Client, error) {
	iface := a2a.NewAgentInterface(endpoint, a2a.TransportProtocolHTTPJSON)
	client, err := a2aclient.NewFromEndpoints(ctx, []*a2a.AgentInterface{iface})
	if err != nil {
		return nil, err
	}
	card, err := client.GetExtendedAgentCard(ctx, &a2a.GetExtendedAgentCardRequest{})
	if err != nil {
		return nil, err
	}
	return &Client{Client: client, card: card}, nil
}

// GetArtifactParts fetches a task and returns all of its artifacts as a single [a2a.Part] slice.
func (s *Client) GetArtifactParts(ctx context.Context, tid a2a.TaskID) ([]*a2a.Part, error) {
	task, err := s.Client.GetTask(ctx, &a2a.GetTaskRequest{ID: tid})
	if err != nil {
		return nil, err
	}
	parts := []*a2a.Part{}
	for _, a := range task.Artifacts {
		for _, p := range a.Parts {
			parts = append(parts, p)
		}
	}
	return parts, nil
}

// SendAll dispatches messages concurrently to the downstream service in non-blocking mode. Returns the IDs of all created tasks.
func (s *Client) SendAll(ctx context.Context, execCtx *a2asrv.ExecutorContext, messages []*a2a.Message, cfg *a2a.PushConfig) ([]a2a.TaskID, error) {
	var mu sync.Mutex
	var errs error
	var subtasks []a2a.TaskID

	var group sync.WaitGroup
	for _, msg := range messages {
		group.Go(func() {
			log.Info(ctx, "dispatching subtask", "parent_id", execCtx.TaskID)

			result, err := s.Client.SendMessage(ctx, &a2a.SendMessageRequest{
				Message:  msg,
				Config:   &a2a.SendMessageConfig{ReturnImmediately: true, PushConfig: cfg},
				Metadata: map[string]any{"parent_task_id": string(execCtx.TaskID)},
			})
			if err != nil {
				mu.Lock()
				errs = errors.Join(errs, fmt.Errorf("swarm message send: %w", err))
				mu.Unlock()
				return
			}

			taskID := result.TaskInfo().TaskID

			mu.Lock()
			subtasks = append(subtasks, taskID)
			mu.Unlock()

			log.Info(ctx, "subtask dispatched", "task_id", taskID, "target", s.card.Name)
		})
	}
	group.Wait()

	if errs != nil {
		return nil, errs
	}
	return subtasks, nil
}
