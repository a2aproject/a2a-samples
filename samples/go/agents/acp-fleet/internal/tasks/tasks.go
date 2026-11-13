// Package tasks fails tasks that no execution will finish: tasks whose
// question nobody answered, and the unfinished tasks of a server that died.
package tasks

import (
	"context"
	"errors"
	"fmt"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/taskstore"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/mysql/store"
)

const maxAttempts = 3

var unfinished = []a2a.TaskState{a2a.TaskStateSubmitted, a2a.TaskStateWorking, a2a.TaskStateInputRequired}

// Reaper writes failures to the task store.
type Reaper struct {
	store  *store.Store
	index  *store.Index
	shards int
	events *events.Publisher
}

// NewReaper returns a reaper of the tasks in s, whose conversations are
// split into count shards. It publishes the tasks it fails to pub.
func NewReaper(s *store.Store, index *store.Index, count int, pub *events.Publisher) *Reaper {
	return &Reaper{store: s, index: index, shards: count, events: pub}
}

// Abandoned stores the event that ends a task whose question nobody answered.
// It implements a2aacp Config.Abandoned.
func (f *Reaper) Abandoned(ctx context.Context, event *a2a.TaskStatusUpdateEvent) {
	if err := f.apply(ctx, event.TaskID, func(*a2a.Task) *a2a.TaskStatusUpdateEvent { return event }); err != nil {
		log.Warn(ctx, "storing an abandoned task failed", "task", event.TaskID, "cause", err)
	}
}

// Orphaned fails the unfinished tasks of the shard's conversations, after the
// server that worked on them died.
func (f *Reaper) Orphaned(ctx context.Context, shard int) {
	for _, state := range unfinished {
		page := ""
		for {
			res, err := f.index.Query(ctx, &store.IndexQueryParams{State: state, PageSize: 100, PageToken: page})
			if err != nil {
				log.Warn(ctx, "listing unfinished tasks failed", "shard", shard, "cause", err)
				return
			}
			for _, t := range res.Tasks {
				if shards.Of(t.ContextID, f.shards) != shard {
					continue
				}
				err := f.apply(ctx, t.ID, func(task *a2a.Task) *a2a.TaskStatusUpdateEvent {
					msg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("The server running this conversation's agent stopped while it worked on this task. Send the message again to continue."))
					return a2a.NewStatusUpdateEvent(task, a2a.TaskStateFailed, msg)
				})
				if err != nil {
					log.Warn(ctx, "failing an orphaned task failed", "task", t.ID, "cause", err)
					continue
				}
				log.Info(ctx, "failed orphaned task", "task", t.ID, "context", t.ContextID, "shard", shard)
				f.events.Publish(ctx, events.Event{Kind: events.TaskFailed, Shard: shard, Context: t.ContextID, Task: string(t.ID)})
			}
			if res.NextPageToken == "" {
				break
			}
			page = res.NextPageToken
		}
	}
}

// apply stores the event that event returns for the current task, unless the task already ended.
func (f *Reaper) apply(ctx context.Context, id a2a.TaskID, event func(*a2a.Task) *a2a.TaskStatusUpdateEvent) error {
	for range maxAttempts {
		stored, err := f.store.Get(ctx, id)
		if err != nil {
			return err
		}
		if stored.Task.Status.State.Terminal() {
			return nil
		}
		e := event(stored.Task)
		next := *stored.Task
		if next.Status.Message != nil {
			next.History = append(append([]*a2a.Message{}, next.History...), next.Status.Message)
		}
		next.Status = e.Status
		_, err = f.store.Update(ctx, &taskstore.UpdateRequest{Task: &next, Event: e, PrevTask: stored.Task, PrevVersion: stored.Version})
		if !errors.Is(err, taskstore.ErrConcurrentModification) {
			return err
		}
	}
	return fmt.Errorf("task %s kept changing", id)
}
