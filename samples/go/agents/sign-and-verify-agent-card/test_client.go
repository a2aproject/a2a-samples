package main

import (
	"context"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"log"
	"net/http"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

// keyProvider fetches and parses public key from JKU URL given key ID (keyID) and JKU URL.
func keyProvider(keyID, jku string) (any, error) {
	if keyID == "" {
		return nil, fmt.Errorf("expected keyID: string, but got empty string")
	}
	if jku == "" {
		return nil, fmt.Errorf("expected jku: string, but got empty string")
	}

	//nolint:gosec // JKU URL is dynamic by design per RFC 7515
	resp, err := http.Get(jku)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch public key from JKU URL (%s): %w", jku, err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch public key from JKU URL (%s): status code %d", jku, resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch public key from JKU URL (%s): failed to read body: %w", jku, err)
	}

	var keys map[string]string
	if unmarshalErr := json.Unmarshal(body, &keys); unmarshalErr != nil {
		return nil, fmt.Errorf("failed to fetch public key from JKU URL (%s): invalid JSON response: %w", jku, unmarshalErr)
	}

	pemStr, ok := keys[keyID]
	if !ok || pemStr == "" {
		return nil, fmt.Errorf("invalid JWK key ID")
	}

	block, _ := pem.Decode([]byte(pemStr))
	if block == nil {
		return nil, fmt.Errorf("failed to decode PEM block for key ID %q", keyID)
	}

	pubKey, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse PKIX public key for key ID %q: %w", keyID, err)
	}

	return pubKey, nil
}

func displayAgentCard(card *a2a.AgentCard) {
	cardJSON, err := json.MarshalIndent(card, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal agent card: %v", err)
	}
	log.Println(string(cardJSON))
}

func runTestClient() {
	ctx := context.Background()
	verifyCardSignature := createSignatureVerifier(keyProvider, []string{es256Alg})

	baseURL := serverURL

	log.Printf("Attempting to fetch public agent card from: %s%s", baseURL, a2asrv.WellKnownAgentCardPath)

	// Initialize A2ACardResolver using SDK helper
	resolver := agentcard.NewResolver(http.DefaultClient)

	// 1. Fetch public agent card without verifying signature
	_, err := resolver.Resolve(ctx, baseURL)
	if err != nil {
		log.Fatalf("Critical error fetching public agent card: %v", err)
	}
	log.Println("Successfully fetched public agent card without verification.")

	// 2. Fetch public agent card and verify signature
	publicCardVerified, err := resolver.Resolve(ctx, baseURL)
	if err != nil {
		log.Fatalf("Critical error fetching public agent card: %v", err)
	}
	if verifyErr := verifyCardSignature(publicCardVerified); verifyErr != nil {
		log.Fatalf("Failed to verify public agent card signature: %v", verifyErr)
	}
	log.Println("Successfully fetched public agent card with verification:")
	displayAgentCard(publicCardVerified)

	// Create A2A Client directly via verified public card
	client, err := a2aclient.NewFromCard(ctx, publicCardVerified)
	if err != nil {
		log.Fatalf("Failed to create A2A client: %v", err)
	}

	// 3. Fetch extended agent card without signature verification
	extendedCardUnverified, err := client.GetExtendedAgentCard(ctx, &a2a.GetExtendedAgentCardRequest{})
	if err != nil {
		log.Fatalf("Failed to get extended agent card: %v", err)
	}
	log.Println("Successfully fetched extended agent card without verification:")
	displayAgentCard(extendedCardUnverified)

	// 4. Fetch extended agent card and verify signature
	extendedCardVerified, err := client.GetExtendedAgentCard(ctx, &a2a.GetExtendedAgentCardRequest{})
	if err != nil {
		log.Fatalf("Failed to get extended agent card: %v", err)
	}
	if verifyErr := verifyCardSignature(extendedCardVerified); verifyErr != nil {
		log.Fatalf("Failed to verify extended agent card signature: %v", verifyErr)
	}
	log.Println("Successfully fetched extended agent card with verification:")
	displayAgentCard(extendedCardVerified)
}
