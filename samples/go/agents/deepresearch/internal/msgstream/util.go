package msgstream

import (
	"context"
	"encoding/json"

	"github.com/nats-io/nats.go/jetstream"
)

// PublishJSON serializes value to JSON and publishes it on the provided subject.
func PublishJSON(ctx context.Context, js jetstream.JetStream, subject string, value any) error {
	msgJSON, err := json.Marshal(value)
	if err != nil {
		return err
	}
	if _, err := js.Publish(ctx, subject, msgJSON); err != nil {
		return err
	}
	return nil
}
