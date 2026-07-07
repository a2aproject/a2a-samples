package main

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"testing"
	"time"

	"samples/go/extensions/timestamp/timestamp"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2aclient/agentcard"
)

var fixedTime = time.Unix(1700000000, 0).UTC()

func TestTimestampExtensionRoundTrip(t *testing.T) {
	ctx := context.Background()
	expectedISO := fixedTime.Format(time.RFC3339Nano)

	ext := timestamp.NewTimestampExtension(timestamp.WithClock(func() time.Time {
		return fixedTime
	}))

	// Setup local in-memory server
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("Failed to listen: %v", err)
	}
	defer listener.Close()

	baseURL := fmt.Sprintf("http://%s", listener.Addr().String())
	serverURL := fmt.Sprintf("%s/invoke", baseURL)

	handler, _ := SetupServerConfig(ext, serverURL)

	server := &http.Server{Handler: handler}
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
