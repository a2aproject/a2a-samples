package timestamp_test

import (
	"context"
	"fmt"
	"iter"
	"net"
	"net/http"
	"testing"
	"time"

	"samples/go/extensions/timestamp"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

var fixedTime = time.Unix(1700000000, 0).UTC()

type echoExecutor struct{}

var _ a2asrv.AgentExecutor = (*echoExecutor)(nil)

func (e *echoExecutor) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		if execCtx.StoredTask == nil {
			task := a2a.NewSubmittedTask(execCtx, execCtx.Message)
			if !yield(task, nil) {
				return
			}
		}

		statusMsg := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("working..."))
		statusUpdate := a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateWorking, statusMsg)
		if !yield(statusUpdate, nil) {
			return
		}

		artEvent := a2a.NewArtifactEvent(execCtx, a2a.NewTextPart("hello!"))
		artEvent.Artifact.Name = "result"
		if !yield(artEvent, nil) {
			return
		}

		completedUpdate := a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCompleted, nil)
		if !yield(completedUpdate, nil) {
			return
		}
	}
}

func (e *echoExecutor) Cancel(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {}
}

func TestTimestampExtensionRoundTrip(t *testing.T) {
	ctx := context.Background()
	expectedISO := fixedTime.Format(time.RFC3339Nano)

	ext := timestamp.NewTimestampExtension(timestamp.WithClock(func() time.Time {
		return fixedTime
	}))

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("Failed to listen: %v", err)
	}
	defer listener.Close()

	baseURL := fmt.Sprintf("http://%s", listener.Addr().String())
	serverURL := fmt.Sprintf("%s/invoke", baseURL)

	card := ext.AddToCard(&a2a.AgentCard{
		Name:        "Echo",
		Description: "echo agent that demonstrates the timestamp extension",
		Version:     "1.0.0",
		SupportedInterfaces: []*a2a.AgentInterface{
			a2a.NewAgentInterface(serverURL, a2a.TransportProtocolJSONRPC),
		},
		DefaultInputModes:  []string{"text"},
		DefaultOutputModes: []string{"text"},
		Capabilities:       a2a.AgentCapabilities{Streaming: true},
	})

	serverInterceptor := timestamp.NewServerInterceptor(ext)
	handler := a2asrv.NewHandler(
		timestamp.WrapExecutor(&echoExecutor{}, ext),
		a2asrv.WithExecutorContextInterceptor(serverInterceptor),
	)
	mux := http.NewServeMux()
	mux.Handle("/invoke", a2asrv.NewJSONRPCHandler(handler))
	mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(card))

	server := &http.Server{Handler: mux}
	go func() {
		_ = server.Serve(listener)
	}()
	defer server.Close()

	// Resolve agent card from server using base URL
	resolvedCard, err := agentcard.DefaultResolver.Resolve(ctx, baseURL)
	if err != nil {
		t.Fatalf("Failed to resolve card: %v", err)
	}

	// Create client with timestamp interceptor
	client, err := a2aclient.NewFromCard(ctx, resolvedCard, a2aclient.WithCallInterceptors(timestamp.ClientInterceptor(ext)))
	if err != nil {
		t.Fatalf("Failed to create client: %v", err)
	}

	req := &a2a.SendMessageRequest{
		Message: a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("hi")),
	}

	var artifacts []*a2a.Artifact
	var statusMessages []*a2a.Message

	for event, err := range client.SendStreamingMessage(ctx, req) {
		if err != nil {
			t.Fatalf("Streaming error: %v", err)
		}
		switch v := event.(type) {
		case *a2a.TaskArtifactUpdateEvent:
			if v.Artifact != nil {
				artifacts = append(artifacts, v.Artifact)
			}
		case *a2a.TaskStatusUpdateEvent:
			if v.Status.Message != nil {
				statusMessages = append(statusMessages, v.Status.Message)
			}
		}
	}

	if len(artifacts) == 0 {
		t.Error("agent did not emit an artifact")
	}
	if len(statusMessages) == 0 {
		t.Error("agent did not emit a status message")
	}

	for _, art := range artifacts {
		ts, ok := art.Meta()[timestamp.TimestampField].(string)
		if !ok || ts != expectedISO {
			t.Errorf("artifact timestamp = %v, want %v", ts, expectedISO)
		}
	}

	for _, msg := range statusMessages {
		ts, ok := msg.Meta()[timestamp.TimestampField].(string)
		if !ok || ts != expectedISO {
			t.Errorf("status message timestamp = %v, want %v", ts, expectedISO)
		}
	}
}
