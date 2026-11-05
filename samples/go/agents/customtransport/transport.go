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
	"fmt"
	"io"
	"iter"
	"net/http"
	"net/url"
	"strings"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/log"
)

const formProtocol a2a.TransportProtocol = "DEMO-FORM"

type formTransport struct {
	endpoint string
	client   *http.Client
}

var _ a2aclient.Transport = (*formTransport)(nil)

func formTransportOption(client *http.Client) a2aclient.FactoryOption {
	return a2aclient.WithTransport(formProtocol, a2aclient.TransportFactoryFn(
		func(_ context.Context, _ *a2a.AgentCard, iface *a2a.AgentInterface) (a2aclient.Transport, error) {
			if iface == nil || iface.URL == "" {
				return nil, fmt.Errorf("missing form endpoint: %w", a2a.ErrInvalidParams)
			}
			return &formTransport{endpoint: iface.URL, client: client}, nil
		},
	))
}

func plainText(msg *a2a.Message) (string, error) {
	if msg == nil || msg.ID == "" || len(msg.Parts) != 1 || msg.Parts[0] == nil {
		return "", fmt.Errorf("expected one identified text message: %w", a2a.ErrInvalidParams)
	}
	part := msg.Parts[0]
	text, ok := part.Content.(a2a.Text)
	if !ok || part.Filename != "" || part.MediaType != "" || len(part.Metadata) != 0 {
		return "", fmt.Errorf("only plain text is supported: %w", a2a.ErrUnsupportedOperation)
	}
	if msg.TaskID != "" || msg.ContextID != "" || len(msg.Extensions) != 0 || len(msg.Metadata) != 0 || len(msg.ReferenceTasks) != 0 {
		return "", fmt.Errorf("task continuation and extensions are not supported: %w", a2a.ErrUnsupportedOperation)
	}
	return string(text), nil
}

func (t *formTransport) SendMessage(ctx context.Context, params a2aclient.ServiceParams, req *a2a.SendMessageRequest) (a2a.SendMessageResult, error) {
	if req == nil || req.Message == nil {
		return nil, fmt.Errorf("missing message: %w", a2a.ErrInvalidParams)
	}
	if req.Tenant != "" || req.Config != nil || len(req.Metadata) != 0 {
		return nil, fmt.Errorf("request options are not supported: %w", a2a.ErrUnsupportedOperation)
	}
	if len(params) != 1 || len(params[a2a.SvcParamVersion]) != 1 {
		return nil, fmt.Errorf("only the protocol version parameter is supported: %w", a2a.ErrUnsupportedOperation)
	}
	if req.Message.Role != a2a.MessageRoleUser {
		return nil, fmt.Errorf("only user messages are supported: %w", a2a.ErrUnsupportedOperation)
	}
	text, err := plainText(req.Message)
	if err != nil {
		return nil, err
	}
	form := url.Values{"id": {req.Message.ID}, "role": {string(req.Message.Role)}, "text": {text}}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, t.endpoint, strings.NewReader(form.Encode()))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	httpReq.Header.Set(a2a.SvcParamVersion, params[a2a.SvcParamVersion][0])
	resp, err := t.client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := resp.Body.Close(); err != nil {
			log.Error(ctx, "failed to close form response body", err)
		}
	}()
	if resp.StatusCode != http.StatusOK {
		body, readErr := io.ReadAll(io.LimitReader(resp.Body, 512))
		if readErr != nil {
			return nil, fmt.Errorf("form server returned %s: %w", resp.Status, readErr)
		}
		return nil, fmt.Errorf("form server returned %s: %s", resp.Status, strings.TrimSpace(string(body)))
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, (1<<16)+1))
	if err != nil {
		return nil, err
	}
	if len(body) > 1<<16 {
		return nil, fmt.Errorf("form response exceeds 64 KiB: %w", a2a.ErrInvalidAgentResponse)
	}
	result, err := url.ParseQuery(string(body))
	if err != nil {
		return nil, err
	}
	if result.Get("id") == "" || result.Get("role") != string(a2a.MessageRoleAgent) || !result.Has("text") {
		return nil, fmt.Errorf("invalid form response: %w", a2a.ErrInvalidAgentResponse)
	}
	message := a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(result.Get("text")))
	message.ID = result.Get("id")
	return message, nil
}

func unsupportedStream() iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) { yield(nil, a2a.ErrUnsupportedOperation) }
}

func (*formTransport) GetTask(context.Context, a2aclient.ServiceParams, *a2a.GetTaskRequest) (*a2a.Task, error) {
	return nil, a2a.ErrUnsupportedOperation
}
func (*formTransport) ListTasks(context.Context, a2aclient.ServiceParams, *a2a.ListTasksRequest) (*a2a.ListTasksResponse, error) {
	return nil, a2a.ErrUnsupportedOperation
}
func (*formTransport) CancelTask(context.Context, a2aclient.ServiceParams, *a2a.CancelTaskRequest) (*a2a.Task, error) {
	return nil, a2a.ErrUnsupportedOperation
}
func (*formTransport) SubscribeToTask(context.Context, a2aclient.ServiceParams, *a2a.SubscribeToTaskRequest) iter.Seq2[a2a.Event, error] {
	return unsupportedStream()
}
func (*formTransport) SendStreamingMessage(context.Context, a2aclient.ServiceParams, *a2a.SendMessageRequest) iter.Seq2[a2a.Event, error] {
	return unsupportedStream()
}
func (*formTransport) GetTaskPushConfig(context.Context, a2aclient.ServiceParams, *a2a.GetTaskPushConfigRequest) (*a2a.PushConfig, error) {
	return nil, a2a.ErrUnsupportedOperation
}
func (*formTransport) ListTaskPushConfigs(context.Context, a2aclient.ServiceParams, *a2a.ListTaskPushConfigRequest) ([]*a2a.PushConfig, error) {
	return nil, a2a.ErrUnsupportedOperation
}
func (*formTransport) CreateTaskPushConfig(context.Context, a2aclient.ServiceParams, *a2a.PushConfig) (*a2a.PushConfig, error) {
	return nil, a2a.ErrUnsupportedOperation
}
func (*formTransport) DeleteTaskPushConfig(context.Context, a2aclient.ServiceParams, *a2a.DeleteTaskPushConfigRequest) error {
	return a2a.ErrUnsupportedOperation
}
func (*formTransport) GetExtendedAgentCard(context.Context, a2aclient.ServiceParams, *a2a.GetExtendedAgentCardRequest) (*a2a.AgentCard, error) {
	return nil, a2a.ErrUnsupportedOperation
}
func (*formTransport) Destroy() error { return nil }

func formServer(handler a2asrv.RequestHandler, endpoint string) http.Handler {
	card := &a2a.AgentCard{
		Name: "Form transport example", Description: "A text-only custom transport demonstration",
		SupportedInterfaces: []*a2a.AgentInterface{a2a.NewAgentInterface(endpoint, formProtocol)},
		DefaultInputModes:   []string{"text"}, DefaultOutputModes: []string{"text"},
		Skills: []a2a.AgentSkill{{ID: "reply", Name: "Reply", Description: "Reply to text", Tags: []string{"demo"}}},
	}
	mux := http.NewServeMux()
	mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(card))
	mux.HandleFunc("POST /exchange", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get(a2a.SvcParamVersion) != string(a2a.Version) {
			http.Error(w, "unsupported A2A version", http.StatusBadRequest)
			return
		}
		if r.Header.Get("Content-Type") != "application/x-www-form-urlencoded" || r.ParseForm() != nil ||
			r.PostForm.Get("id") == "" || r.PostForm.Get("role") != string(a2a.MessageRoleUser) || !r.PostForm.Has("text") {
			http.Error(w, "invalid form message", http.StatusBadRequest)
			return
		}
		msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(r.PostForm.Get("text")))
		msg.ID = r.PostForm.Get("id")
		ctx, _ := a2asrv.NewCallContext(r.Context(), a2asrv.NewServiceParams(r.Header))
		result, err := handler.SendMessage(ctx, &a2a.SendMessageRequest{Message: msg})
		if err != nil {
			log.Error(r.Context(), "send message failed", err)
			http.Error(w, "message processing failed", http.StatusInternalServerError)
			return
		}
		response, ok := result.(*a2a.Message)
		if !ok {
			http.Error(w, "task results are not supported", http.StatusNotImplemented)
			return
		}
		text, err := plainText(response)
		if err != nil {
			http.Error(w, err.Error(), http.StatusNotImplemented)
			return
		}
		w.Header().Set("Content-Type", "application/x-www-form-urlencoded")
		if _, err := io.WriteString(w, url.Values{"id": {response.ID}, "role": {string(response.Role)}, "text": {text}}.Encode()); err != nil {
			return
		}
	})
	return mux
}
