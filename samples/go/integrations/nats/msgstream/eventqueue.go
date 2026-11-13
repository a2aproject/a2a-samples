// Package msgstream provides NATS JetStream-backed event queues, work queues, and push notification senders.
package msgstream

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/eventqueue"
	"github.com/nats-io/nats.go/jetstream"
)

const (
	eventsStream = "EVENTS"
)

type natsEventQueueManager struct {
	stream jetstream.Stream
	policy jetstream.DeliverPolicy
}

var _ eventqueue.Manager = (*natsEventQueueManager)(nil)

// CreateEventReplayManager returns an [eventqueue.Manager] that replays all events from the beginning of the stream.
func CreateEventReplayManager(ctx context.Context, js jetstream.JetStream) (eventqueue.Manager, error) {
	stream, err := js.Stream(ctx, eventsStream)
	if err != nil {
		return nil, fmt.Errorf("nats events stream: %v", err)
	}
	return &natsEventQueueManager{stream, jetstream.DeliverAllPolicy}, nil
}

// CreateEventQueueManager returns an [eventqueue.Manager] that delivers only new events.
func CreateEventQueueManager(ctx context.Context, js jetstream.JetStream) (eventqueue.Manager, error) {
	stream, err := js.Stream(ctx, eventsStream)
	if err != nil {
		return nil, fmt.Errorf("nats events stream: %v", err)
	}
	return &natsEventQueueManager{stream, jetstream.DeliverNewPolicy}, nil
}

// CreateReader implements [eventqueue.Manager.CreateReader].
func (m *natsEventQueueManager) CreateReader(ctx context.Context, taskID a2a.TaskID) (eventqueue.Reader, error) {
	cons, err := m.stream.OrderedConsumer(ctx, jetstream.OrderedConsumerConfig{
		FilterSubjects: []string{eventsSubject(taskID)},
		DeliverPolicy:  m.policy,
	})
	if err != nil {
		return nil, fmt.Errorf("ordered consumer for %s: %w", taskID, err)
	}

	msgChan := make(chan jetstream.Msg, 64)
	var cc jetstream.ConsumeContext
	cc, err = cons.Consume(func(msg jetstream.Msg) {
		select {
		case msgChan <- msg:
		case <-cc.Closed():
		}
	})
	if err != nil {
		return nil, fmt.Errorf("consume %s: %w", taskID, err)
	}
	return &natsEventReader{msgChan: msgChan, cc: cc}, nil
}

// CreateWriter implements [eventqueue.Manager.CreateWriter].
func (m *natsEventQueueManager) CreateWriter(_ context.Context, _ a2a.TaskID) (eventqueue.Writer, error) {
	return natsNoOpWriter{}, nil
}

// Destroy implements [eventqueue.Manager.Destroy].
func (m *natsEventQueueManager) Destroy(_ context.Context, _ a2a.TaskID) error {
	return nil
}

type natsEventReader struct {
	msgChan chan jetstream.Msg
	cc      jetstream.ConsumeContext
}

// Read implements [eventqueue.Reader.Read].
func (r *natsEventReader) Read(ctx context.Context) (*eventqueue.Message, error) {
	select {
	case <-ctx.Done():
		return nil, ctx.Err()

	case natsMsg, ok := <-r.msgChan:
		if !ok {
			return nil, eventqueue.ErrQueueClosed
		}
		var msg eventqueue.Message
		if err := json.Unmarshal(natsMsg.Data(), &msg); err != nil {
			return nil, fmt.Errorf("message parsing: %w", err)
		}
		return &msg, nil
	}
}

// Close implements [eventqueue.Reader.Close].
func (r *natsEventReader) Close() error {
	r.cc.Stop()
	return nil
}

// natsNoOpWriter is a no-op because events are written through the task store.
type natsNoOpWriter struct{}

// Write implements [eventqueue.Writer.Write].
func (natsNoOpWriter) Write(context.Context, *eventqueue.Message) error { return nil }

// Close implements [eventqueue.Writer.Close].
func (natsNoOpWriter) Close() error { return nil }

// natsEventWriter publishes events from the outbox relay to the EVENTS stream.
type natsEventWriter struct {
	js jetstream.JetStream
}

// NewEventWriter creates an [eventqueue.Writer] that publishes to the EVENTS stream.
func NewEventWriter(js jetstream.JetStream) eventqueue.Writer {
	return &natsEventWriter{js: js}
}

func (w *natsEventWriter) Write(ctx context.Context, msg *eventqueue.Message) error {
	if err := PublishJSON(ctx, w.js, eventsSubject(msg.Event.TaskInfo().TaskID), msg); err != nil {
		return fmt.Errorf("nats publish: %w", err)
	}
	return nil
}

func (w *natsEventWriter) Close() error { return nil }

func eventsSubject(tid a2a.TaskID) string {
	return "events." + string(tid)
}
