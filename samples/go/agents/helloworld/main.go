package main

import (
	"log"
	"net/http"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

const textPlain = "text/plain"

func main() {
	// --8<-- [start:AgentSkill]
	// Defines the abilities or functions that agent can perform.
	skill := a2a.AgentSkill{
		ID:          "echo_bot",
		Name:        "Echo Bot",
		Description: "An example agent that acknowledges client request and responds with a \"Hello World\" message.",
		InputModes:  []string{textPlain},
		OutputModes: []string{textPlain},
		Tags:        []string{"a2a", "echo-example"},
		Examples:    []string{"hi", "how are you"},
	}
	// --8<-- [end:AgentSkill]

	// Defines an optional additional skill for the agent that is not visible in the public card.
	extendedSkill := a2a.AgentSkill{
		ID:          "echo_bot_super_mode",
		Name:        "Echo Bot (Super Mode)",
		Description: "An extended version of Echo Bot that responds with extra enthusiasm!",
		Tags:        []string{"a2a", "echo-example", "extended"},
		Examples:    []string{"super hi", "give me a super hello"},
	}

	// --8<-- [start:AgentCard]
	// Define a public-facing agent card that allows clients to discover your agent's capabilities.
	publicAgentCard := &a2a.AgentCard{
		// Basic identity information of A2A server
		Name:        "Hello World Agent", // Identity
		Description: "Just a hello world agent",
		Version:     "0.0.1",
		// Default Media Types for the agent's interactions
		DefaultInputModes:  []string{textPlain}, // Supported media types
		DefaultOutputModes: []string{textPlain},
		// Supported A2A features (like streaming or extended config)
		Capabilities: a2a.AgentCapabilities{Streaming: true, ExtendedAgentCard: true},
		// Ordered list of endpoints and protocols where the service can be reached
		SupportedInterfaces: []*a2a.AgentInterface{
			{
				ProtocolBinding: a2a.TransportProtocolJSONRPC,
				ProtocolVersion: a2a.Version,
				URL:             "http://127.0.0.1:9999",
			},
		},
		// The list of AgentSkill objects that this agent offers
		Skills: []a2a.AgentSkill{skill},
	}
	// --8<-- [end:AgentCard]

	// Defines the authenticated extended agent card with
	// extended skills that are visible only to authenticated users
	extendedAgentCard := &a2a.AgentCard{
		Name:               "Hello World Agent - Extended Edition",
		Description:        "The full-featured hello world agent for authenticated users.",
		Version:            "0.0.2",
		DefaultInputModes:  []string{textPlain},
		DefaultOutputModes: []string{textPlain},
		Capabilities:       a2a.AgentCapabilities{Streaming: true, ExtendedAgentCard: true},
		SupportedInterfaces: []*a2a.AgentInterface{
			{
				ProtocolBinding: a2a.TransportProtocolJSONRPC,
				ProtocolVersion: a2a.Version,
				URL:             "http://127.0.0.1:9999",
			},
		},
		Skills: []a2a.AgentSkill{
			skill,
			extendedSkill,
		}, // Both skills for the extended card
	}

	// --8<-- [start:RequestHandler]
	// The RequestHandler processes incoming requests and manages tasks
	requestHandler := a2asrv.NewHandler(
		// Agent executor handles the execution of the client requests
		NewHelloWorldAgentExecutor(),
		// Extended agent card for authenticated users
		a2asrv.WithExtendedAgentCard(extendedAgentCard),
	)
	// --8<-- [end:RequestHandler]

	// --8<-- [start:ServerRoutes]
	// Creating the routes for the A2A server
	mux := http.NewServeMux()

	// Create routes for the agent card
	mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(publicAgentCard))

	// Create routes for the JSONRPC protocol
	mux.Handle("/", a2asrv.NewJSONRPCHandler(requestHandler))
	// --8<-- [end:ServerRoutes]

	// --8<-- [start:AppServer]
	server := &http.Server{
		Addr:              "127.0.0.1:9999",
		Handler:           mux,
		ReadHeaderTimeout: 3 * time.Second,
	}

	go func() {
		log.Println("Starting A2A server on http://127.0.0.1:9999...")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	time.Sleep(150 * time.Millisecond)

	runInteractiveClient()
	// --8<-- [end:AppServer]
}
