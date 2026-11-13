package msgstream

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/push"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

const natsURLScheme = "nats://"

// PushSenderConfig configures a NATS-backed [push.Sender].
type PushSenderConfig struct {
	Jetstream jetstream.JetStream
}

// NewPushSender creates a [push.Sender] that publishes status updates to NATS subjects.
func NewPushSender(cfg PushSenderConfig) push.Sender {
	return &natsPushSender{cfg}
}

// NewPushConfig creates a [a2a.PushConfig] that routes push notifications to the given NATS subject.
func NewPushConfig(subject string, token string) *a2a.PushConfig {
	return &a2a.PushConfig{URL: natsURLScheme + subject, Token: token}
}

// natsPushSender implements push.Sender by publishing status update events
// to a NATS JetStream subject. Only handles PushConfig URLs with the [natsURLScheme].
type natsPushSender struct {
	PushSenderConfig
}

var _ push.Sender = (*natsPushSender)(nil)

// SendPush implements [push.Sender.SendPush].
func (s *natsPushSender) SendPush(ctx context.Context, config *a2a.PushConfig, event a2a.Event) error {
	su, ok := event.(*a2a.TaskStatusUpdateEvent)
	if !ok {
		return nil
	}

	subject, ok := strings.CutPrefix(config.URL, natsURLScheme)
	if !ok {
		return nil
	}

	data, err := json.Marshal(a2a.StreamResponse{Event: event})
	if err != nil {
		return fmt.Errorf("marshal push event: %w", err)
	}

	if _, err := s.Jetstream.PublishMsg(ctx, &nats.Msg{
		Subject: subject,
		Header:  nats.Header{"A2A-Token": []string{config.Token}},
		Data:    data,
	}); err != nil {
		return fmt.Errorf("nats publish push to %s: %w", subject, err)
	}

	log.Debug(ctx, "push notification sent", "subject", subject, "status", su.Status.State, "task_id", su.TaskID)

	return nil
}
