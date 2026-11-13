// Package natstest connects integration tests to a NATS server, such as the
// one in this module's compose.yaml.
package natstest

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

// URL is the NATS server URL used by integration tests.
const URL = nats.DefaultURL

// EventsStream is the configuration of the stream read by the event queues of [msgstream].
var EventsStream = jetstream.StreamConfig{
	Name:      "EVENTS",
	Subjects:  []string{"events.>"},
	Retention: jetstream.LimitsPolicy,
	Storage:   jetstream.FileStorage,
}

// WorkStream is the configuration of the stream read by the work queues of [msgstream].
var WorkStream = jetstream.StreamConfig{
	Name:      "WORK",
	Subjects:  []string{"work.>"},
	Retention: jetstream.WorkQueuePolicy,
	Storage:   jetstream.FileStorage,
}

// Connect connects to [URL], retrying for up to 15 seconds while the server starts.
func Connect(t testing.TB) (*nats.Conn, jetstream.JetStream) {
	t.Helper()
	var nc *nats.Conn
	var err error
	for deadline := time.Now().Add(15 * time.Second); time.Now().Before(deadline); time.Sleep(500 * time.Millisecond) {
		if nc, err = nats.Connect(URL); err == nil {
			break
		}
	}
	if err != nil {
		t.Fatalf("nats.Connect(%q) error = %v", URL, err)
	}
	t.Cleanup(nc.Close)
	js, err := jetstream.New(nc)
	if err != nil {
		t.Fatalf("jetstream.New() error = %v", err)
	}
	return nc, js
}

// ResetStreams deletes the streams and creates them again, so that a test starts from a clean state.
func ResetStreams(t testing.TB, js jetstream.JetStream, cfgs ...jetstream.StreamConfig) {
	t.Helper()
	ctx := context.Background()
	for _, cfg := range cfgs {
		if err := js.DeleteStream(ctx, cfg.Name); err != nil && !errors.Is(err, jetstream.ErrStreamNotFound) {
			t.Fatalf("js.DeleteStream(%q) error = %v", cfg.Name, err)
		}
		if _, err := js.CreateStream(ctx, cfg); err != nil {
			t.Fatalf("js.CreateStream(%q) error = %v", cfg.Name, err)
		}
	}
}

// ResetKeyValue deletes the bucket, so that a test starts without it.
func ResetKeyValue(t testing.TB, js jetstream.JetStream, bucket string) {
	t.Helper()
	if err := js.DeleteKeyValue(context.Background(), bucket); err != nil && !errors.Is(err, jetstream.ErrBucketNotFound) {
		t.Fatalf("js.DeleteKeyValue(%q) error = %v", bucket, err)
	}
}
