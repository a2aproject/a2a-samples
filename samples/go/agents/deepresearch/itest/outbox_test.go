package itest_test

import (
	"context"
	"database/sql"
	"testing"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/eventqueue"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/lease"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/msgstream"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/store"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/testutil"
	"github.com/nats-io/nats.go/jetstream"
)

func TestOutbox_RelaysToNATS(t *testing.T) {
	testutil.SetupNATS(t)
	testutil.SetupMySQL(t)

	_, js := testutil.ConnectNATS(t)

	db, err := sql.Open("mysql", testutil.MySQLDSN)
	if err != nil {
		t.Fatalf("mysql open: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	ctx, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)

	lm, err := lease.CreateManager(ctx, js, jetstream.KeyValueConfig{
		Bucket: "OUTBOX_TEST",
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

	// Insert event into outbox table.
	taskID := a2a.NewTaskID()
	now := time.Now()
	task := &a2a.Task{
		ID:        taskID,
		ContextID: "ctx-outbox",
		Status:    a2a.TaskStatus{State: a2a.TaskStateSubmitted, Timestamp: &now},
	}
	msg := &eventqueue.Message{Event: task, TaskVersion: 1, Protocol: a2a.Version}

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatalf("begin tx: %v", err)
	}
	if insertErr := outbox.Insert(ctx, tx, msg); insertErr != nil {
		t.Fatalf("outbox insert: %v", insertErr)
	}
	if commitErr := tx.Commit(); commitErr != nil {
		t.Fatalf("commit: %v", commitErr)
	}

	// Start outbox relay.
	go outbox.Run(ctx) //nolint:errcheck // test background goroutine

	// Verify the event appears in NATS.
	eventsStream, err := js.Stream(ctx, "EVENTS")
	if err != nil {
		t.Fatalf("get EVENTS stream: %v", err)
	}
	cons, err := eventsStream.OrderedConsumer(ctx, jetstream.OrderedConsumerConfig{
		FilterSubjects: []string{"events." + string(taskID)},
	})
	if err != nil {
		t.Fatalf("ordered consumer: %v", err)
	}

	batch, err := cons.Fetch(1, jetstream.FetchMaxWait(5*time.Second))
	if err != nil {
		t.Fatalf("fetch: %v", err)
	}
	count := 0
	for range batch.Messages() {
		count++
	}
	if count == 0 {
		t.Fatal("outbox did not relay event to NATS within timeout")
	}

	// Verify the outbox table is drained (retry because the delete runs
	// asynchronously after the NATS publish).
	waitForOutboxDrain(ctx, t, db)
}

func waitForOutboxDrain(ctx context.Context, t *testing.T, db *sql.DB) {
	t.Helper()
	deadline := time.After(2 * time.Second)
	for {
		var remaining int
		if err := db.QueryRowContext(ctx, "SELECT COUNT(*) FROM outbox").Scan(&remaining); err != nil {
			t.Fatalf("count outbox rows: %v", err)
		}
		if remaining == 0 {
			return
		}
		select {
		case <-deadline:
			t.Fatalf("outbox still has %d rows after timeout", remaining)
		case <-time.After(50 * time.Millisecond):
		}
	}
}
