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

// Package main provides an example of a custom A2A client transport.
package main

import (
	"context"
	"fmt"
	"iter"
	"log"
	"net"
	"net/http"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

func main() {
	ctx := context.Background()
	executor := a2asrv.AgentExecutorFunc(func(_ context.Context, _ *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
		return func(yield func(a2a.Event, error) bool) {
			yield(a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("Hello from the form transport!")), nil)
		}
	})
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	baseURL := "http://" + listener.Addr().String()
	server := &http.Server{Handler: formServer(a2asrv.NewHandler(executor), baseURL+"/exchange")}
	go func() {
		if err := server.Serve(listener); err != nil && err != http.ErrServerClosed {
			log.Printf("form server: %v", err)
		}
	}()
	defer func() {
		if err := server.Shutdown(ctx); err != nil {
			log.Printf("shutdown: %v", err)
		}
	}()

	card, err := agentcard.DefaultResolver.Resolve(ctx, baseURL)
	if err != nil {
		log.Fatal(err)
	}
	client, err := a2aclient.NewFromCard(ctx, card, a2aclient.WithDefaultsDisabled(), formTransportOption(http.DefaultClient))
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		if err := client.Destroy(); err != nil {
			log.Printf("destroy transport: %v", err)
		}
	}()
	result, err := client.SendMessage(ctx, &a2a.SendMessageRequest{Message: a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("Hello"))})
	if err != nil {
		log.Fatal(err)
	}
	message, ok := result.(*a2a.Message)
	if !ok || len(message.Parts) != 1 {
		log.Fatalf("unexpected response: %T", result)
	}
	fmt.Println(message.Parts[0].Text())
}
