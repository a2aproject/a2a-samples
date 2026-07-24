// Package statemachine provides a generic event-sourced state machine driven by NATS JetStream.
package statemachine

import (
	"context"
	"errors"
	"time"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/nats-io/nats.go/jetstream"
)

var ErrStopped = errors.New("stopped")

// Spec describes a generic event-sourced state machine parameterized by event type E and state type S.
type Spec[E, S any] struct {
	// Subject filters events belonging to this particular state machine instance.
	Subject string
	// State is the initial state to which replayed events will be applied.
	State S
	// Decode converts a raw NATS message into a typed event.
	Decode func(context.Context, jetstream.Msg) (E, error)
	// Evolve applies an event to the state (pure state transition, no side effects).
	Evolve func(context.Context, S, E) error
	// Act inspects the current state after catch-up and decides on side effects. Returns true when done.
	Act func(context.Context, S, []E) error
}

// Run replays existing events, catches up, and then enters the act loop until done or error.
func Run[E, S any](ctx context.Context, stream jetstream.Stream, spec Spec[E, S]) error {
	defer log.Info(ctx, "state machine done")

	cons, err := stream.OrderedConsumer(ctx, jetstream.OrderedConsumerConfig{
		FilterSubjects: []string{spec.Subject},
		DeliverPolicy:  jetstream.DeliverAllPolicy,
	})
	if err != nil {
		return err
	}
	var caughtUp bool
	for {
		var batch jetstream.MessageBatch
		if caughtUp {
			batch, err = cons.Fetch(100, jetstream.FetchMaxWait(10*time.Millisecond))
		} else {
			batch, err = cons.FetchNoWait(100)
		}
		if err != nil {
			return err
		}

		var events []E
		for msg := range batch.Messages() {
			event, err := spec.Decode(ctx, msg)
			if err != nil {
				return err
			}
			events = append(events, event)

			if evolveErr := spec.Evolve(ctx, spec.State, event); evolveErr != nil {
				return evolveErr
			}
			meta, err := msg.Metadata()
			if err != nil {
				return err
			}
			caughtUp = caughtUp || (meta.NumPending == 0)
		}
		caughtUp = caughtUp || len(events) == 0

		if batch.Error() != nil {
			return batch.Error()
		}

		log.Debug(ctx, "batch processed", "size", len(events), "caugh_up", caughtUp)

		if caughtUp {
			if err := spec.Act(ctx, spec.State, events); err != nil {
				return err
			}
		}
	}
}
