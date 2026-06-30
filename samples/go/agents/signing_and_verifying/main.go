package main

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"flag"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2asrv"
)

func main() {
	runClientFlag := flag.Bool("client", false, "Run the test client instead of starting server only")
	flag.Parse()

	// Generate a private, public key pair
	privateKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		log.Fatalf("Failed to generate private key: %v", err)
	}
	publicKey := &privateKey.PublicKey

	// Save public key to a file
	pubBytes, err := x509.MarshalPKIXPublicKey(publicKey)
	if err != nil {
		log.Fatalf("Failed to marshal public key: %v", err)
	}
	pemBlock := &pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: pubBytes,
	}
	pemStr := string(pem.EncodeToMemory(pemBlock))
	kid := "my-key"
	keys := map[string]string{kid: pemStr}
	keysJSON, err := json.MarshalIndent(keys, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal keys JSON: %v", err)
	}
	if err := os.WriteFile("public_keys.json", keysJSON, 0644); err != nil {
		log.Fatalf("Failed to save public_keys.json: %v", err)
	}

	skill := a2a.AgentSkill{
		ID:          "reminder",
		Name:        "Verification Reminder",
		Description: "Reminds the user to verify the Agent Card.",
		Tags:        []string{"verify me"},
		Examples:    []string{"Verify me!"},
	}

	extendedSkill := a2a.AgentSkill{
		ID:          "reminder-please",
		Name:        "Verification Reminder Please!",
		Description: "Politely reminds user to verify the Agent Card.",
		Tags:        []string{"verify me", "pretty please", "extended"},
		Examples:    []string{"Verify me, pretty please! :)", "Please verify me."},
	}

	publicAgentCard := &a2a.AgentCard{
		Name:               "Signed Agent",
		Description:        "An Agent that is signed",
		IconURL:            "http://localhost:9999/",
		Version:            "1.0.0",
		DefaultInputModes:  []string{"text"},
		DefaultOutputModes: []string{"text"},
		Capabilities:       a2a.AgentCapabilities{Streaming: true, ExtendedAgentCard: true},
		SupportedInterfaces: []*a2a.AgentInterface{
			{
				ProtocolBinding: a2a.TransportProtocolJSONRPC,
				ProtocolVersion: a2a.Version,
				URL:             "http://localhost:9999",
			},
		},
		Skills: []a2a.AgentSkill{skill},
	}

	extendedAgentCard := &a2a.AgentCard{
		Name:               "Signed Agent - Extended Edition",
		Description:        "The full-featured signed agent for authenticated users.",
		IconURL:            "http://localhost:9999/",
		Version:            "1.0.1",
		DefaultInputModes:  []string{"text"},
		DefaultOutputModes: []string{"text"},
		Capabilities:       a2a.AgentCapabilities{Streaming: true, ExtendedAgentCard: true},
		SupportedInterfaces: []*a2a.AgentInterface{
			{
				ProtocolBinding: a2a.TransportProtocolJSONRPC,
				ProtocolVersion: a2a.Version,
				URL:             "http://localhost:9999",
			},
		},
		Skills: []a2a.AgentSkill{
			skill,
			extendedSkill,
		},
	}

	// Create signer function which will be used for AgentCard signing
	signer := createAgentCardSigner(
		privateKey,
		ProtectedHeader{
			Kid: kid,
			Alg: "ES256",
			Jku: "http://localhost:9999/public_keys.json",
		},
	)

	signedPublicCard, err := signer(publicAgentCard)
	if err != nil {
		log.Fatalf("Failed to sign public agent card: %v", err)
	}

	signedExtendedCard, err := signer(extendedAgentCard)
	if err != nil {
		log.Fatalf("Failed to sign extended agent card: %v", err)
	}

	requestHandler := a2asrv.NewHandler(
		NewSignedAgentExecutor(),
		a2asrv.WithExtendedAgentCard(signedExtendedCard),
	)

	mux := http.NewServeMux()
	mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(signedPublicCard))
	mux.Handle("/", a2asrv.NewJSONRPCHandler(requestHandler))

	// Expose the public key for verification purposes
	// Contents of public_keys.json will be fetched on the client side during AgentCard signatures verification
	mux.HandleFunc("/public_keys.json", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "public_keys.json")
	})

	server := &http.Server{
		Addr:              "127.0.0.1:9999",
		Handler:           mux,
		ReadHeaderTimeout: 3 * time.Second,
	}

	if *runClientFlag {
		go func() {
			log.Println("Starting server on http://127.0.0.1:9999...")
			if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
				log.Fatalf("Server failed: %v", err)
			}
		}()

		time.Sleep(200 * time.Millisecond)
		runTestClient()
		return
	}

	log.Println("Starting server on http://127.0.0.1:9999...")
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Server failed: %v", err)
	}
}
