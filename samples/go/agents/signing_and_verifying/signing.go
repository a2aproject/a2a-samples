package main

import (
	"crypto/ecdsa"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/golang-jwt/jwt/v5"
)

// Sentinel errors for signature verification matching Python SDK exception types.
var (
	ErrNoSignature       = errors.New("AgentCard has no signatures to verify")
	ErrInvalidSignatures = errors.New("no valid signature found")
)

// ProtectedHeader defines the protected header parameters for JWS (RFC 7515).
type ProtectedHeader struct {
	Kid string `json:"kid"`
	Alg string `json:"alg,omitempty"`
	Jku string `json:"jku,omitempty"`
	Typ string `json:"typ,omitempty"`
}

// KeyProvider is a function type that returns a verification key (e.g., *ecdsa.PublicKey) for a given kid and jku.
type KeyProvider func(kid, jku string) (any, error)

func cleanEmpty(v any) any {
	switch val := v.(type) {
	case map[string]any:
		cleanedMap := make(map[string]any)
		for k, item := range val {
			if cleanedItem := cleanEmpty(item); cleanedItem != nil {
				cleanedMap[k] = cleanedItem
			}
		}
		if len(cleanedMap) == 0 {
			return nil
		}
		return cleanedMap
	case []any:
		var cleanedList []any
		for _, item := range val {
			if cleanedItem := cleanEmpty(item); cleanedItem != nil {
				cleanedList = append(cleanedList, cleanedItem)
			}
		}
		if len(cleanedList) == 0 {
			return nil
		}
		return cleanedList
	case string:
		if val == "" {
			return nil
		}
		return val
	default:
		return val
	}
}

// canonicalizeAgentCard produces canonical JSON according to RFC 8785 (JCS).
func canonicalizeAgentCard(card *a2a.AgentCard) ([]byte, error) {
	data, err := json.Marshal(card)
	if err != nil {
		return nil, err
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}
	delete(raw, "signatures")

	cleaned := cleanEmpty(raw)
	if cleaned == nil {
		return []byte("{}"), nil
	}
	return json.Marshal(cleaned)
}

// createAgentCardSigner creates a function that signs an AgentCard and appends the signature.
func createAgentCardSigner(privateKey *ecdsa.PrivateKey, protectedHeader ProtectedHeader) func(card *a2a.AgentCard) (*a2a.AgentCard, error) {
	if protectedHeader.Alg == "" {
		protectedHeader.Alg = es256Alg
	}

	method := jwt.GetSigningMethod(protectedHeader.Alg)

	return func(card *a2a.AgentCard) (*a2a.AgentCard, error) {
		if method == nil {
			return nil, fmt.Errorf("unsupported signing algorithm: %s", protectedHeader.Alg)
		}

		cardCopy := *card
		cardCopy.Signatures = append([]a2a.AgentCardSignature(nil), card.Signatures...)

		canonPayload, err := canonicalizeAgentCard(&cardCopy)
		if err != nil {
			return nil, fmt.Errorf("failed to canonicalize agent card: %w", err)
		}

		protectedBytes, err := json.Marshal(protectedHeader)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal protected header: %w", err)
		}
		protectedB64 := base64.RawURLEncoding.EncodeToString(protectedBytes)
		payloadB64 := base64.RawURLEncoding.EncodeToString(canonPayload)

		signingInput := protectedB64 + "." + payloadB64

		sigBytes, err := method.Sign(signingInput, privateKey)
		if err != nil {
			return nil, fmt.Errorf("failed to sign agent card: %w", err)
		}

		sig := a2a.AgentCardSignature{
			Protected: protectedB64,
			Signature: base64.RawURLEncoding.EncodeToString(sigBytes),
		}

		cardCopy.Signatures = append(cardCopy.Signatures, sig)
		return &cardCopy, nil
	}
}

// createSignatureVerifier creates a function that verifies the signatures on an AgentCard.
func createSignatureVerifier(keyProvider KeyProvider, allowedAlgs []string) func(card *a2a.AgentCard) error {
	return func(card *a2a.AgentCard) error {
		if len(card.Signatures) == 0 {
			return ErrNoSignature
		}

		canonPayload, err := canonicalizeAgentCard(card)
		if err != nil {
			return fmt.Errorf("failed to canonicalize agent card: %w", err)
		}
		payloadB64 := base64.RawURLEncoding.EncodeToString(canonPayload)

		for _, sig := range card.Signatures {
			protectedBytes, err := base64.RawURLEncoding.DecodeString(sig.Protected)
			if err != nil {
				continue
			}
			var protectedHeader ProtectedHeader
			if unmarshalErr := json.Unmarshal(protectedBytes, &protectedHeader); unmarshalErr != nil {
				continue
			}

			algAllowed := false
			for _, alg := range allowedAlgs {
				if protectedHeader.Alg == alg {
					algAllowed = true
					break
				}
			}
			if !algAllowed {
				continue
			}

			verificationKey, err := keyProvider(protectedHeader.Kid, protectedHeader.Jku)
			if err != nil {
				continue
			}

			tokenStr := sig.Protected + "." + payloadB64 + "." + sig.Signature
			token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (any, error) {
				if token.Method.Alg() != protectedHeader.Alg {
					return nil, fmt.Errorf("unexpected signing algorithm: %v", token.Header["alg"])
				}
				return verificationKey, nil
			})

			if err == nil && token.Valid {
				return nil
			}
		}

		return ErrInvalidSignatures
	}
}
