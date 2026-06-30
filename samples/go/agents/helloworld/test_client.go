package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2aclient"
	"github.com/a2aproject/a2a-go/a2asrv"
)

const serverURL = "http://127.0.0.1:9999"

func getAgentCard(ctx context.Context) (*a2a.AgentCard, error) {
	fmt.Println("Initializes the A2ACardResolver instance with an HTTP client")

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, serverURL+a2asrv.WellKnownAgentCardPath, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch agent card: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch agent card: status code %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read agent card body: %w", err)
	}

	var card a2a.AgentCard
	if err := json.Unmarshal(body, &card); err != nil {
		return nil, fmt.Errorf("failed to unmarshal agent card: %w", err)
	}

	fmt.Println("\nSuccessfully fetched the public agent card:")
	return &card, nil
}

//nolint:unused
func displayAgentCard(card *a2a.AgentCard) {
	fmt.Println("====================================================")
	fmt.Println("                    AgentCard                      ")
	fmt.Println("====================================================")
	fmt.Println("--- General ---")
	fmt.Printf("Name        : %s\n", card.Name)
	fmt.Printf("Description : %s\n", card.Description)
	fmt.Printf("Version     : %s\n", card.Version)
	fmt.Println("\n--- Interfaces ---")
	for i, iface := range card.SupportedInterfaces {
		fmt.Printf("  [%d] %s  (%s)\n", i, iface.URL, iface.ProtocolBinding)
	}
	fmt.Println("\n--- Capabilities ---")
	fmt.Printf("Streaming           : %t\n", card.Capabilities.Streaming)
	fmt.Printf("Push notifications  : %t\n", card.Capabilities.PushNotifications)
	fmt.Printf("Extended agent card : %t\n", card.Capabilities.ExtendedAgentCard)
}

//nolint:unused
func showAgentCard(ctx context.Context) {
	card, err := getAgentCard(ctx)
	if err != nil {
		log.Fatalf("Error fetching agent card: %v", err)
	}
	displayAgentCard(card)
}

func sendMessage(ctx context.Context, textQuery string) {
	card, err := getAgentCard(ctx)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Println("\n--- Public Agent Card - Non-Streaming Call ---")
	fmt.Println("\nInitializing a non-streaming client.")

	client, err := a2aclient.NewFromCard(ctx, card)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}

	msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(textQuery))
	req := &a2a.SendMessageRequest{Message: msg}

	fmt.Println("Response:")
	res, err := client.SendMessage(ctx, req)
	if err != nil {
		log.Fatalf("SendMessage failed: %v", err)
	}
	fmt.Printf("%+v\n", res)
}

//nolint:unused
func sendStreamingMessage(ctx context.Context, textQuery string) {
	card, err := getAgentCard(ctx)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(textQuery))
	req := &a2a.SendMessageRequest{Message: msg}

	fmt.Println("\n--- Public Agent Card - Streaming Call ---")
	fmt.Println("\nInitializing a streaming client.")

	client, err := a2aclient.NewFromCard(ctx, card)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}

	fmt.Println("Response:")
	events := client.SendStreamingMessage(ctx, req)
	for ev, err := range events {
		if err != nil {
			log.Fatalf("Streaming error: %v", err)
		}
		fmt.Printf("%+v\n", ev)
	}
}

//nolint:unused
func showExtendedCard(ctx context.Context) {
	card, err := getAgentCard(ctx)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	client, err := a2aclient.NewFromCard(ctx, card)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}

	fmt.Println("\n--- Extended Agent Card - Non-Streaming Call ---")
	extendedCard, err := client.GetExtendedAgentCard(ctx, &a2a.GetExtendedAgentCardRequest{})
	if err != nil {
		log.Fatalf("GetExtendedAgentCard failed: %v", err)
	}
	fmt.Println("\nSuccessfully fetched the authenticated extended agent card:")
	displayAgentCard(extendedCard)
}

//nolint:unused
func testClientWorkflow(ctx context.Context, textQuery string) {
	showAgentCard(ctx)
	sendMessage(ctx, textQuery)
	sendStreamingMessage(ctx, textQuery)
	showExtendedCard(ctx)
}

func runInteractiveClient() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()

	fmt.Println("\nStarting an interactive session with A2A Server [http://127.0.0.1:9999]")
	fmt.Println("Use `exit` to quit.")

	reader := bufio.NewReader(os.Stdin)
	fmt.Print("user > ")
	prompt, err := reader.ReadString('\n')
	if err != nil {
		return
	}
	prompt = strings.TrimSpace(prompt)

	for prompt != "" && prompt != "exit" {
		sendMessage(ctx, prompt)
		fmt.Print("--\nuser > ")
		prompt, err = reader.ReadString('\n')
		if err != nil {
			return
		}
		prompt = strings.TrimSpace(prompt)
	}
}
