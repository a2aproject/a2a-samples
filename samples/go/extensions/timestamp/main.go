package main

import (
	"fmt"
	"net/http"
	"os"

	"samples/go/extensions/timestamp/timestamp_ext"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

// SetupServerConfig sets up the HTTP handler and agent card for the server.
func SetupServerConfig(ext *timestamp_ext.TimestampExtension, invokeURL string) (http.Handler, *a2a.AgentCard) {
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

	serverInterceptor := timestamp_ext.NewServerInterceptor(ext)
	handler := a2asrv.NewHandler(
		timestamp_ext.WrapExecutor(newEchoExecutor(), ext),
		a2asrv.WithExecutorContextInterceptor(serverInterceptor),
	)

	mux := http.NewServeMux()
	mux.Handle("/invoke", a2asrv.NewJSONRPCHandler(handler))
	mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(card))

	return mux, card
}

func main() {
	ext := timestamp_ext.NewTimestampExtension()
	port := "9998"
	invokeURL := fmt.Sprintf("http://127.0.0.1:%s/invoke", port)

	handler, _ := SetupServerConfig(ext, invokeURL)

	fmt.Printf("Echo agent server running on http://127.0.0.1:%s\n", port)
	if err := http.ListenAndServe("127.0.0.1:"+port, handler); err != nil {
		fmt.Fprintf(os.Stderr, "Server failed: %v\n", err)
		os.Exit(1)
	}
}
