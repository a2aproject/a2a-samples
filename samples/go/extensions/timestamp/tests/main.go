package main

import (
	"context"
	"fmt"
	"iter"
	"net/http"
	"os"

	"samples/go/extensions/timestamp/timestamp"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

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

// SetupServerConfig sets up the HTTP handler and agent card for the server.
func SetupServerConfig(ext *timestamp.TimestampExtension, invokeURL string) (http.Handler, *a2a.AgentCard) {
	card := ext.AddToCard(&a2a.AgentCard{
		Name:        "Echo",
		Description: "echo agent that demonstrates the timestamp extension",
		Version:     "1.0.0",
		SupportedInterfaces: []*a2a.AgentInterface{
			a2a.NewAgentInterface(invokeURL, a2a.TransportProtocolJSONRPC),
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

	return mux, card
}

func main() {
	ext := timestamp.NewTimestampExtension()
	port := "9998"
	invokeURL := fmt.Sprintf("http://127.0.0.1:%s/invoke", port)

	handler, _ := SetupServerConfig(ext, invokeURL)

	fmt.Printf("Echo agent server running on http://127.0.0.1:%s\n", port)
	if err := http.ListenAndServe("127.0.0.1:"+port, handler); err != nil {
		fmt.Fprintf(os.Stderr, "Server failed: %v\n", err)
		os.Exit(1)
	}
}
