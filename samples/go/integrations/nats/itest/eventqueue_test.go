package itest_test

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/eventqueue"
	"github.com/a2aproject/a2a-go/v2/a2asrv/taskstore"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/nats/msgstream"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/nats/natstest"
)

func TestEventQueue_WriteAndReplay(t *testing.T) {
	_, js := natstest.Connect(t)
	natstest.ResetStreams(t, js, natstest.EventsStream)

	ctx := context.Background()

	writer := msgstream.NewEventWriter(js)
	task := &a2a.Task{ID: a2a.NewTaskID(), ContextID: a2a.NewContextID(), Status: a2a.TaskStatus{State: a2a.TaskStateSubmitted}}
	msg1 := &eventqueue.Message{Event: task, TaskVersion: 1, Protocol: a2a.Version}
	if err := writer.Write(ctx, msg1); err != nil {
		t.Fatalf("write task event: %v", err)
	}

	statusUpdate := a2a.NewStatusUpdateEvent(msg1.Event, a2a.TaskStateWorking, nil)
	msg2 := &eventqueue.Message{Event: statusUpdate, TaskVersion: 2, Protocol: a2a.Version}
	if err := writer.Write(ctx, msg2); err != nil {
		t.Fatalf("write status event: %v", err)
	}

	replayMgr, err := msgstream.CreateEventReplayManager(ctx, js)
	if err != nil {
		t.Fatalf("create replay manager: %v", err)
	}
	reader, err := replayMgr.CreateReader(ctx, msg1.Event.TaskInfo().TaskID)
	if err != nil {
		t.Fatalf("create reader: %v", err)
	}
	t.Cleanup(func() { _ = reader.Close() })

	readCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	for i, wantMsg := range []*eventqueue.Message{msg1, msg2} {
		gotMsg, err := reader.Read(readCtx)
		if err != nil {
			t.Fatalf("read event %d: %v", i, err)
		}
		if gotMsg.TaskVersion != wantMsg.TaskVersion {
			t.Errorf("event %d version: got %d, want %v", i, gotMsg.TaskVersion, wantMsg.TaskVersion)
		}
		gotType, wantType := fmt.Sprintf("%T", gotMsg.Event), fmt.Sprintf("%T", wantMsg.Event)
		if gotType != wantType {
			t.Errorf("event %d type: got %T, want %T", i, gotType, wantType)
		}
	}
}

func TestEventQueue_LiveReaderSkipsUserMessages(t *testing.T) {
	_, js := natstest.Connect(t)
	natstest.ResetStreams(t, js, natstest.EventsStream)
	ctx := context.Background()

	live, err := msgstream.CreateEventQueueManager(ctx, js)
	if err != nil {
		t.Fatalf("msgstream.CreateEventQueueManager() error = %v", err)
	}
	task := &a2a.Task{ID: a2a.NewTaskID(), ContextID: a2a.NewContextID(), Status: a2a.TaskStatus{State: a2a.TaskStateInputRequired}}
	reader, err := live.CreateReader(ctx, task.ID)
	if err != nil {
		t.Fatalf("live.CreateReader() error = %v", err)
	}
	t.Cleanup(func() { _ = reader.Close() })

	reply := a2a.NewMessageForTask(a2a.MessageRoleUser, task, a2a.NewTextPart("once"))
	working := a2a.NewStatusUpdateEvent(task, a2a.TaskStateWorking, nil)
	writer := msgstream.NewEventWriter(js)
	for i, event := range []a2a.Event{reply, working} {
		if err := writer.Write(ctx, &eventqueue.Message{Event: event, TaskVersion: taskstore.TaskVersion(i + 2), Protocol: a2a.Version}); err != nil {
			t.Fatalf("writer.Write() error = %v", err)
		}
	}

	readCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	got, err := reader.Read(readCtx)
	if err != nil {
		t.Fatalf("reader.Read() error = %v", err)
	}
	if _, ok := got.Event.(*a2a.TaskStatusUpdateEvent); !ok {
		t.Fatalf("reader.Read() = %T, want the status update after the user's message", got.Event)
	}
}
