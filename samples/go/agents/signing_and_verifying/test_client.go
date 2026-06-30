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

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2aclient"
	"github.com/a2aproject/a2a-go/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/a2asrv"
)

func keyProvider(kid, jku string) (any, error) {
	if kid == "" || jku == "" {
		log.Println("kid or jku missing")
		return nil, fmt.Errorf("kid or jku missing")
	}

	//nolint:gosec // JKU URL is dynamic by design per RFC 7515
	resp, err := http.Get(jku)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch jku: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("jku request failed with status: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read jku body: %w", err)
	}

	var keys map[string]string
	if unmarshalErr := json.Unmarshal(body, &keys); unmarshalErr != nil {
		return nil, fmt.Errorf("failed to unmarshal keys JSON: %w", unmarshalErr)
	}

	pemStr, ok := keys[kid]
	if !ok {
		return nil, fmt.Errorf("key id %s not found in jku", kid)
	}

	block, _ := pem.Decode([]byte(pemStr))
	if block == nil {
		return nil, fmt.Errorf("failed to decode PEM block")
	}

	pubKey, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse PKIX public key: %w", err)
	}

	return pubKey, nil
}

func runTestClient() {
	ctx := context.Background()
	signatureVerifier := createSignatureVerifier(keyProvider, []string{es256Alg})

	baseURL := serverURL

	log.Printf("Attempting to fetch public agent card from: %s%s", baseURL, a2asrv.WellKnownAgentCardPath)

	// Initialize A2ACardResolver
	resolver := agentcard.NewResolver(http.DefaultClient)
	publicCard, err := resolver.Resolve(ctx, baseURL)
	if err != nil {
		log.Fatalf("Critical error fetching public agent card: %v", err)
	}

	// Verifies the AgentCard using signature_verifier function before returning it
	if verifyErr := signatureVerifier(publicCard); verifyErr != nil {
		log.Fatalf("Failed to verify public agent card signature: %v", verifyErr)
	}

	log.Println("Successfully fetched public agent card:")
	cardJSON, err := json.MarshalIndent(publicCard, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal public agent card: %v", err)
	}
	log.Println(string(cardJSON))
	log.Println("\nUsing PUBLIC agent card for client initialization (default).")

	// Create Base Client directly via unified factory
	client, err := a2aclient.NewFromCard(ctx, publicCard)
	if err != nil {
		log.Fatalf("Failed to create A2A client: %v", err)
	}

	extendedCard, err := client.GetExtendedAgentCard(ctx, &a2a.GetExtendedAgentCardRequest{})
	if err != nil {
		log.Fatalf("Failed to get extended agent card: %v", err)
	}

	// Verifies the AgentCard using signature_verifier function before returning it
	if verifyErr := signatureVerifier(extendedCard); verifyErr != nil {
		log.Fatalf("Failed to verify extended agent card signature: %v", verifyErr)
	}

	fmt.Println("Fetched extended card:")
	extJSON, err := json.MarshalIndent(extendedCard, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal extended agent card: %v", err)
	}
	fmt.Println(string(extJSON))
}
