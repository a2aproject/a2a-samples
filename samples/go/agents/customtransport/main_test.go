// Copyright 2026 The A2A Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"errors"
	"fmt"
	"iter"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

func TestCustomTransport(t *testing.T) {
	t.Parallel()
	executor := a2asrv.AgentExecutorFunc(func(_ context.Context, _ *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
		return func(yield func(a2a.Event, error) bool) {
			yield(a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("reply")), nil)
		}
	})
	handler := a2asrv.NewHandler(executor)
	type formRequest struct {
		id      string
		role    string
		text    string
		version string
	}
	requests := make(chan formRequest, 1)
	var server *httptest.Server
	server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/exchange" {
			if err := r.ParseForm(); err != nil {
				t.Errorf("ParseForm() error = %v, want nil", err)
			} else {
				requests <- formRequest{r.PostForm.Get("id"), r.PostForm.Get("role"), r.PostForm.Get("text"), r.Header.Get(a2a.SvcParamVersion)}
			}
		}
		formServer(handler, server.URL+"/exchange").ServeHTTP(w, r)
	}))
	defer server.Close()

	ctx := t.Context()
	card, err := agentcard.DefaultResolver.Resolve(ctx, server.URL)
	if err != nil {
		t.Fatalf("Resolve() error = %v, want nil", err)
	}
	if got := card.SupportedInterfaces[0].ProtocolBinding; got != formProtocol {
		t.Fatalf("protocol = %q, want %q", got, formProtocol)
	}
	client, err := a2aclient.NewFromCard(ctx, card, a2aclient.WithDefaultsDisabled(), formTransportOption(server.Client()))
	if err != nil {
		t.Fatalf("NewFromCard() error = %v, want nil", err)
	}
	defer func() {
		if err := client.Destroy(); err != nil {
			t.Errorf("Destroy() error = %v, want nil", err)
		}
	}()
	request := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("hello"))
	result, err := client.SendMessage(ctx, &a2a.SendMessageRequest{Message: request})
	if err != nil {
		t.Fatalf("SendMessage() error = %v, want nil", err)
	}
	wire := <-requests
	if wire.id != request.ID || wire.role != string(a2a.MessageRoleUser) || wire.text != "hello" || wire.version != string(a2a.Version) {
		t.Fatalf("form request = %+v, want ID %s, role %s, text hello, version %s", wire, request.ID, a2a.MessageRoleUser, a2a.Version)
	}
	msg, ok := result.(*a2a.Message)
	if !ok || len(msg.Parts) != 1 || msg.Parts[0].Text() != "reply" {
		t.Fatalf("SendMessage() = %v, want reply message", result)
	}
	_, err = client.GetTask(ctx, &a2a.GetTaskRequest{ID: "missing"})
	if !errors.Is(err, a2a.ErrUnsupportedOperation) {
		t.Fatalf("GetTask() error = %v, want %v", err, a2a.ErrUnsupportedOperation)
	}
}

func TestOversizedResponse(t *testing.T) {
	t.Parallel()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, err := fmt.Fprint(w, url.Values{
			"id": {"reply"}, "role": {string(a2a.MessageRoleAgent)}, "text": {strings.Repeat("x", 1<<16)},
		}.Encode())
		if err != nil {
			t.Errorf("write response: %v", err)
		}
	}))
	defer server.Close()
	transport := &formTransport{endpoint: server.URL, client: server.Client()}
	_, err := transport.SendMessage(t.Context(), a2aclient.ServiceParams{a2a.SvcParamVersion: {string(a2a.Version)}},
		&a2a.SendMessageRequest{Message: a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("hello"))})
	if !errors.Is(err, a2a.ErrInvalidAgentResponse) {
		t.Fatalf("SendMessage() error = %v, want %v", err, a2a.ErrInvalidAgentResponse)
	}
}

func TestFormServerRejectsWrongVersion(t *testing.T) {
	t.Parallel()
	server := httptest.NewServer(formServer(nil, "http://example.test/exchange"))
	defer server.Close()
	req, err := http.NewRequestWithContext(t.Context(), http.MethodPost, server.URL+"/exchange", strings.NewReader("id=1&role=ROLE_USER&text=hello"))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	resp, err := server.Client().Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusBadRequest)
	}
}

func TestUnsupportedInput(t *testing.T) {
	t.Parallel()
	transport := &formTransport{endpoint: "http://127.0.0.1/exchange", client: http.DefaultClient}
	for _, tc := range []struct {
		name string
		msg  *a2a.Message
	}{
		{name: "binary", msg: a2a.NewMessage(a2a.MessageRoleUser, a2a.NewRawPart([]byte("binary")))},
		{name: "continuation", msg: func() *a2a.Message {
			msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("text"))
			msg.TaskID = "existing"
			return msg
		}()},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			_, err := transport.SendMessage(t.Context(), a2aclient.ServiceParams{a2a.SvcParamVersion: {string(a2a.Version)}}, &a2a.SendMessageRequest{Message: tc.msg})
			if !errors.Is(err, a2a.ErrUnsupportedOperation) {
				t.Fatalf("SendMessage() error = %v, want %v", err, a2a.ErrUnsupportedOperation)
			}
		})
	}
}
