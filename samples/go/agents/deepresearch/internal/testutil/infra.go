package testutil

import (
	"context"
	"database/sql"
	"testing"
	"time"

	_ "github.com/go-sql-driver/mysql" // MySQL driver registration
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

const (
	// NatsURL is the NATS server URL used by integration tests.
	NatsURL = nats.DefaultURL
	// MySQLDSN is the MySQL connection string used by integration tests.
	MySQLDSN = "root:root@tcp(localhost:3306)/planner?parseTime=true"
)

// SetupNATS deletes and recreates all JetStream streams, consumers, and KV
// buckets so every test run starts from a clean state. It retries the
// connection for up to 15 seconds to allow for container startup.
func SetupNATS(t *testing.T) {
	t.Helper()
	var nc *nats.Conn
	var err error
	deadline := time.Now().Add(15 * time.Second)
	for time.Now().Before(deadline) {
		nc, err = nats.Connect(NatsURL)
		if err == nil {
			break
		}
		time.Sleep(500 * time.Millisecond)
	}
	if err != nil {
		t.Fatalf("NATS not available at %s after retries: %v", NatsURL, err)
	}
	t.Cleanup(nc.Close)

	js, err := jetstream.New(nc)
	if err != nil {
		t.Fatalf("jetstream init: %v", err)
	}
	ctx := context.Background()

	// Clean slate.
	for _, name := range []string{"EVENTS", "WORK", "STATES"} {
		js.DeleteStream(ctx, name) //nolint:errcheck // cleanup, may not exist
	}
	js.DeleteKeyValue(ctx, "OUTBOX") //nolint:errcheck // cleanup, may not exist

	// Streams.
	for _, cfg := range []jetstream.StreamConfig{
		{Name: "EVENTS", Subjects: []string{"events.>"}, Retention: jetstream.LimitsPolicy, Storage: jetstream.FileStorage},
		{Name: "WORK", Subjects: []string{"work.>"}, Retention: jetstream.WorkQueuePolicy, Storage: jetstream.FileStorage},
		{Name: "STATES", Subjects: []string{"states.>"}, Retention: jetstream.LimitsPolicy, MaxAge: 24 * time.Hour, Storage: jetstream.MemoryStorage},
	} {
		if _, createErr := js.CreateStream(ctx, cfg); createErr != nil {
			t.Fatalf("create stream %s: %v", cfg.Name, createErr)
		}
	}

	// Per-agent consumers on the WORK stream.
	work, err := js.Stream(ctx, "WORK")
	if err != nil {
		t.Fatalf("get WORK stream: %v", err)
	}
	for _, agent := range []string{"orchestrator", "researcher", "analyzer", "synthesizer"} {
		if _, err := work.CreateOrUpdateConsumer(ctx, jetstream.ConsumerConfig{
			Name:          agent,
			FilterSubject: "work." + agent,
			AckPolicy:     jetstream.AckExplicitPolicy,
			DeliverPolicy: jetstream.DeliverAllPolicy,
		}); err != nil {
			t.Fatalf("create consumer %s: %v", agent, err)
		}
	}
}

// SetupMySQL ensures the schema exists and truncates all rows. It calls
// t.Fatal if MySQL is unreachable.
func SetupMySQL(t *testing.T) {
	t.Helper()
	db, err := sql.Open("mysql", MySQLDSN)
	if err != nil {
		t.Fatalf("MySQL open: %v", err)
	}
	defer db.Close()

	deadline := time.Now().Add(15 * time.Second)
	for time.Now().Before(deadline) {
		if err := db.Ping(); err == nil {
			break
		}
		time.Sleep(500 * time.Millisecond)
	}
	if err := db.Ping(); err != nil {
		t.Fatalf("MySQL not reachable after retries: %v", err)
	}

	for _, ddl := range []string{
		`CREATE TABLE IF NOT EXISTS tasks (
			task_id    CHAR(36) PRIMARY KEY,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
			user       VARCHAR(255) NOT NULL DEFAULT '',
			agent      VARCHAR(255) NOT NULL DEFAULT '',
			context_id VARCHAR(255) NOT NULL DEFAULT '',
			state      VARCHAR(32)  NOT NULL DEFAULT 'submitted',
			version    BIGINT       NOT NULL DEFAULT 1
		) ENGINE=InnoDB`,
		`CREATE TABLE IF NOT EXISTS outbox (
			id         BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			task_id    CHAR(36) NOT NULL,
			event_data TEXT NOT NULL
		) ENGINE=InnoDB`,
	} {
		if _, err := db.Exec(ddl); err != nil {
			t.Fatalf("schema DDL: %v", err)
		}
	}

	for _, table := range []string{"outbox", "tasks"} {
		if _, err := db.Exec("DELETE FROM " + table); err != nil { //nolint:gosec // table names are hardcoded constants
			t.Fatalf("truncate %s: %v", table, err)
		}
	}
}

// ConnectNATS creates a nats connection to [NatsURL] and initializes a jetstream client.
func ConnectNATS(t *testing.T) (*nats.Conn, jetstream.JetStream) {
	t.Helper()
	nc, err := nats.Connect(NatsURL)
	if err != nil {
		t.Fatalf("nats connect: %v", err)
	}
	t.Cleanup(nc.Close)
	js, err := jetstream.New(nc)
	if err != nil {
		t.Fatalf("jetstream: %v", err)
	}
	return nc, js
}
