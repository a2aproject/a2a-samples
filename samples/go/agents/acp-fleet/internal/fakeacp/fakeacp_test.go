package fakeacp_test

import (
	"context"
	"io"
	"strings"
	"sync"
	"testing"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/integrations/executor/a2aacp"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/fakeacp"
)

type pipes struct {
	io.Reader
	io.WriteCloser
}

type sessions struct {
	mu sync.Mutex
	m  map[string]a2aacp.Session
}

func (s *sessions) Get(_ context.Context, id string) (a2aacp.Session, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.m[id]
	return v, ok, nil
}

func (s *sessions) Put(_ context.Context, id string, v a2aacp.Session) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.m[id] = v
	return nil
}

func newHandler(t *testing.T, server, home string, store a2aacp.SessionStore) a2asrv.RequestHandler {
	t.Helper()
	start := a2aacp.AgentFunc(func(context.Context, string) (io.ReadWriteCloser, error) {
		agentIn, toAgent := io.Pipe()
		fromAgent, agentOut := io.Pipe()
		go func() {
			err := fakeacp.Run(fakeacp.Config{Server: server, Home: home}, agentIn, agentOut)
			agentOut.CloseWithError(err)
		}()
		return pipes{Reader: fromAgent, WriteCloser: toAgent}, nil
	})
	exec, err := a2aacp.NewExecutor(context.Background(), start, &a2aacp.Config{
		Pool:         &a2aacp.PoolConfig{},
		SessionStore: store,
		Session: func(context.Context, *a2asrv.ExecutorContext) (a2aacp.SessionParams, error) {
			return a2aacp.SessionParams{Cwd: t.TempDir()}, nil
		},
	})
	if err != nil {
		t.Fatalf("a2aacp.NewExecutor() error = %v", err)
	}
	t.Cleanup(func() {
		if err := exec.Close(); err != nil {
			t.Errorf("exec.Close() error = %v", err)
		}
	})
	return a2asrv.NewHandler(exec)
}

func send(t *testing.T, h a2asrv.RequestHandler, contextID string, taskID a2a.TaskID, text string) *a2a.Task {
	t.Helper()
	msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(text))
	msg.ContextID, msg.TaskID = contextID, taskID
	res, err := h.SendMessage(context.Background(), &a2a.SendMessageRequest{Message: msg})
	if err != nil {
		t.Fatalf("SendMessage(%q) error = %v", text, err)
	}
	task, ok := res.(*a2a.Task)
	if !ok {
		t.Fatalf("SendMessage(%q) = %T, want *a2a.Task", text, res)
	}
	return task
}

func reply(task *a2a.Task) string {
	var sb strings.Builder
	for _, art := range task.Artifacts {
		for _, p := range art.Parts {
			sb.WriteString(p.Text())
		}
	}
	return sb.String()
}

func TestRun_conversationQuestionAndLoad(t *testing.T) {
	t.Parallel()
	home := t.TempDir()
	store := &sessions{m: map[string]a2aacp.Session{}}
	h := newHandler(t, "server-1", home, store)
	ctxID := a2a.NewContextID()

	if got := reply(send(t, h, ctxID, "", "hi")); !strings.Contains(got, "server-1: turn 1, new session") {
		t.Fatalf("first reply = %q, want a new session", got)
	}
	asked := send(t, h, ctxID, "", "save milk")
	if asked.Status.State != a2a.TaskStateInputRequired {
		t.Fatalf("save state = %v, want input-required", asked.Status.State)
	}
	if got := reply(send(t, h, ctxID, asked.ID, "once")); !strings.Contains(got, "saved. Notes: milk") {
		t.Fatalf("answered reply = %q, want the saved note", got)
	}

	other := newHandler(t, "server-2", home, store)
	got := reply(send(t, other, ctxID, "", "again"))
	want := "server-2: turn 3, session loaded; turns 1-2 ran on server-1. Earlier you said: hi | save milk. Notes: milk"
	if got != want {
		t.Fatalf("reply after load = %q, want %q", got, want)
	}
}
