package itest_test

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/msgstream"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/statemachine"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/testutil"
	"github.com/nats-io/nats.go/jetstream"
)

func TestStateMachine_Adder(t *testing.T) {
	testutil.SetupNATS(t)

	_, js := testutil.ConnectNATS(t)

	ctx := context.Background()
	subject := "states.test-sm"

	for i := 1; i <= 3; i++ {
		if err := msgstream.PublishJSON(ctx, js, subject, i); err != nil {
			t.Fatalf("publish event %d: %v", i, err)
		}
	}

	stream, err := js.Stream(ctx, "STATES")
	if err != nil {
		t.Fatalf("get STATES stream: %v", err)
	}

	type state struct{ Sum int }
	s := &state{}
	var actCalled bool
	err = statemachine.Run(ctx, stream, statemachine.Spec[int, *state]{
		Subject: subject,
		State:   s,
		Decode: func(_ context.Context, msg jetstream.Msg) (int, error) {
			var v int
			return v, json.Unmarshal(msg.Data(), &v)
		},
		Evolve: func(_ context.Context, s *state, v int) error {
			s.Sum += v
			return nil
		},
		Act: func(_ context.Context, s *state, _ []int) error {
			actCalled = true
			if s.Sum >= 6 { // 1+2+3 = 6
				return statemachine.ErrStopped
			}
			return nil
		},
	})

	if err != nil && !errors.Is(err, statemachine.ErrStopped) {
		t.Fatalf("state machine run: %v", err)
	}
	if s.Sum != 6 {
		t.Errorf("final sum: got %d, want 6", s.Sum)
	}
	if !actCalled {
		t.Error("Act was never called")
	}
}
