package msgstream

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/workqueue"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/nats-io/nats.go/jetstream"
)

const (
	workStream  = "WORK"
	workSubject = "work"
)

type natsWorkReadWriter struct {
	jetsteam jetstream.JetStream
	consumer jetstream.Consumer
	subject  string
}

var _ workqueue.ReadWriter = (*natsWorkReadWriter)(nil)

// CreateWorkQueue creates a NATS-backed pull work queue for the given agent type.
func CreateWorkQueue(ctx context.Context, js jetstream.JetStream, agentType domain.AgentType) (workqueue.Queue, error) {
	ws, err := js.Stream(ctx, workStream)
	if err != nil {
		return nil, fmt.Errorf("nats %q stream: %w", workStream, err)
	}
	cons, err := ws.Consumer(ctx, string(agentType))
	if err != nil {
		return nil, fmt.Errorf("nats %q stream %q consumer: %w", workStream, agentType, err)
	}
	subject := workSubject + "." + string(agentType)
	readWriter := &natsWorkReadWriter{jetsteam: js, consumer: cons, subject: subject}
	return workqueue.NewPullQueue(readWriter, nil), nil
}

func (rw *natsWorkReadWriter) Write(ctx context.Context, p *workqueue.Payload) (a2a.TaskID, error) {
	if err := PublishJSON(ctx, rw.jetsteam, rw.subject, p); err != nil {
		return "", fmt.Errorf("js publish: %w", err)
	}
	log.Info(ctx, "work item published", "task_id", p.TaskID, "type", p.Type, "subject", rw.subject)
	return p.TaskID, nil
}

// Read blocks until a work item is available. It polls NATS Fetch in a loop
// because Fetch returns an empty batch (no error) on timeout.
func (rw *natsWorkReadWriter) Read(ctx context.Context) (workqueue.Message, error) {
	for ctx.Err() == nil {
		batch, err := rw.consumer.Fetch(1, jetstream.FetchMaxWait(1*time.Minute))
		if err != nil {
			return nil, fmt.Errorf("js fetch: %w", err)
		}

		for msg := range batch.Messages() {
			var p workqueue.Payload
			if err := json.Unmarshal(msg.Data(), &p); err != nil {
				_ = msg.Nak()
				return nil, fmt.Errorf("unmarshal payload: %w", err)
			}

			log.Info(ctx, "work item dequeued", "task_id", p.TaskID, "type", p.Type)

			return &natsWorkMsg{payload: &p, msg: msg}, nil
		}

		if err := batch.Error(); err != nil {
			return nil, err
		}
		// Empty batch, retry.
	}
	return nil, ctx.Err()
}

type natsWorkMsg struct {
	payload *workqueue.Payload
	msg     jetstream.Msg
}

var (
	_ workqueue.Message     = (*natsWorkMsg)(nil)
	_ workqueue.Heartbeater = (*natsWorkMsg)(nil)
)

// Payload implements [workqueue.Message.Payload].
func (m *natsWorkMsg) Payload() *workqueue.Payload { return m.payload }

// Complete implements [workqueue.Message.Complete].
func (m *natsWorkMsg) Complete(ctx context.Context) error { return m.msg.Ack() }

// Return implements [workqueue.Message.Return].
func (m *natsWorkMsg) Return(ctx context.Context, cause error) error {
	log.Warn(ctx, "work item returned (nak)", "task_id", m.payload.TaskID, "cause", cause)
	return m.msg.Nak()
}

// HeartbeatInterval returns the interval at which InProgress signals are sent
// to NATS, preventing the ack timeout from expiring during long-running tasks.
func (m *natsWorkMsg) HeartbeatInterval() time.Duration { return time.Second }

// Heartbeat signals NATS that this message is still being processed.
func (m *natsWorkMsg) Heartbeat(_ context.Context) error { return m.msg.InProgress() }
