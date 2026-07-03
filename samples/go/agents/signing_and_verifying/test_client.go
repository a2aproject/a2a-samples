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

// keyProvider fetches and parses public key from JKU URL given key ID (kid) and JKU URL.
func keyProvider(kid, jku string) (any, error) {
	if kid == "" {
		return nil, fmt.Errorf("expected kid: string, but got empty string")
	}
	if jku == "" {
		return nil, fmt.Errorf("expected jku: string, but got empty string")
	}

	//nolint:gosec // JKU URL is dynamic by design per RFC 7515
	resp, err := http.Get(jku)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch public key from JKU URL (%s): %w", jku, err)
	}
	defer resp.Body.Close()

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

	pemStr, ok := keys[kid]
	if !ok || pemStr == "" {
		return nil, fmt.Errorf("invalid JWK Key ID.")
	}

	block, _ := pem.Decode([]byte(pemStr))
	if block == nil {
		return nil, fmt.Errorf("failed to decode PEM block for key ID %q", kid)
	}

	pubKey, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse PKIX public key for key ID %q: %w", kid, err)
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
	publicCard, err := resolver.Resolve(ctx, baseURL)
	if err != nil {
		log.Fatalf("Critical error fetching public agent card: %v", err)
	}

	// Pass verifyCardSignature to validate the signature on the public Agent Card
	if verifyErr := verifyCardSignature(publicCard); verifyErr != nil {
		log.Fatalf("Failed to verify public agent card signature: %v", verifyErr)
	}

	log.Println("Successfully fetched public agent card:")

	// Create A2A Client directly via unified card
	client, err := a2aclient.NewFromCard(ctx, publicCard)
	if err != nil {
		log.Fatalf("Failed to create A2A client: %v", err)
	}

	// Pass verifyCardSignature to validate the signature on the extended Agent Card
	extendedCardWithSignature, err := client.GetExtendedAgentCard(ctx, &a2a.GetExtendedAgentCardRequest{})
	if err != nil {
		log.Fatalf("Failed to get extended agent card: %v", err)
	}
	if verifyErr := verifyCardSignature(extendedCardWithSignature); verifyErr != nil {
		log.Fatalf("Failed to verify extended agent card signature: %v", verifyErr)
	}

	log.Println("Successfully fetched extended agent card with signature:")
	displayAgentCard(extendedCardWithSignature)
	log.Println("Signature:")
	sigJSON, err := json.MarshalIndent(extendedCardWithSignature.Signatures, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal signature: %v", err)
	}
	log.Println(string(sigJSON))

	// Fetch extended card without signature verification (signature verification is optional on client side)
	extendedCardWithoutSignature, err := client.GetExtendedAgentCard(ctx, &a2a.GetExtendedAgentCardRequest{})
	if err != nil {
		log.Fatalf("Failed to get extended agent card without signature check: %v", err)
	}

	log.Println("Successfully fetched extended agent card without signature:")
	displayAgentCard(extendedCardWithoutSignature)
}
