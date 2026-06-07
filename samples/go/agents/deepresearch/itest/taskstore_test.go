package itest_test

import (
	"context"
	"database/sql"
	"testing"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/lease"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/msgstream"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/store"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/testutil"
	"github.com/nats-io/nats.go/jetstream"
)

// TestTaskStore_CreateAndGet verifies the full task lifecycle: create persists
// to MySQL + outbox, the outbox relays to NATS, and Get materializes from
// the event replay.
func TestTaskStore_CreateAndGet(t *testing.T) {
	testutil.SetupNATS(t)
	testutil.SetupMySQL(t)

	_, js := testutil.ConnectNATS(t)

	db, err := sql.Open("mysql", testutil.MySQLDSN)
	if err != nil {
		t.Fatalf("mysql open: %v", err)
	}
	t.Cleanup(func() { db.Close() })

	ctx, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)

	lm, err := lease.CreateManager(ctx, js, jetstream.KeyValueConfig{
		Bucket: "TASKSTORE_TEST",
		TTL:    10 * time.Second,
	})
	if err != nil {
		t.Fatalf("lease manager: %v", err)
	}

	outbox, err := store.NewOutbox(store.OutboxConfig{
		DB:           db,
		Agent:        domain.AgentResearcher,
		Writer:       msgstream.NewEventWriter(js),
		Interval:     50 * time.Millisecond,
		LeaseManager: lm,
	})
	if err != nil {
		t.Fatalf("create outbox: %v", err)
	}
	go func() { _ = outbox.Run(ctx) }()

	replayMgr, err := msgstream.CreateEventReplayManager(ctx, js)
	if err != nil {
		t.Fatalf("create replay manager: %v", err)
	}

	taskStore := store.New(store.Config{
		DB:          db,
		Outbox:      outbox,
		TaskIndex:   store.NewIndex(db),
		EventReplay: replayMgr,
	})

	// Create a task.
	task := &a2a.Task{ID: a2a.NewTaskID(), ContextID: a2a.NewContextID(), Status: a2a.TaskStatus{State: a2a.TaskStateSubmitted}}
	version, err := taskStore.Create(ctx, task)
	if err != nil {
		t.Fatalf("store.Create: %v", err)
	}

	// Wait for the outbox to relay the event.
	time.Sleep(300 * time.Millisecond)

	// Get the task back via event replay.
	stored, err := taskStore.Get(ctx, task.ID)
	if err != nil {
		t.Fatalf("store.Get: %v", err)
	}
	if stored.Task.ID != task.ID {
		t.Errorf("task ID: got %s, want %s", stored.Task.ID, task.ID)
	}
	if stored.Task.Status.State != a2a.TaskStateSubmitted {
		t.Errorf("task state: got %s, want submitted", stored.Task.Status.State)
	}
	if stored.Version != version {
		t.Errorf("version: got %d, want %d", stored.Version, version)
	}
}
