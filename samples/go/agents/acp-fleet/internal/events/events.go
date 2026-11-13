// Package events publishes what the servers of the fleet do, for the watch
// view. Events are best effort: a server that can't publish one goes on.
package events

import (
	"context"
	"encoding/json"
	"strings"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/nats-io/nats.go"
)

// Subject is the subject prefix of the events; the kind is appended.
const Subject = "fleet.events"

const snippetLen = 80

// Kind is the kind of an event.
type Kind string

const (
	// Routed is published by the server that took a message from the load
	// balancer, after the owner of its conversation's shard accepted it.
	Routed Kind = "routed"
	// AgentStarted and AgentStopped track the agent processes of a server.
	AgentStarted Kind = "agent-started"
	AgentStopped Kind = "agent-stopped"
	// TurnStarted and TurnEnded bracket the agent's work on a message.
	TurnStarted Kind = "turn-started"
	TurnEnded   Kind = "turn-ended"
	// Claimed and Released are published when a shard moves.
	Claimed  Kind = "claimed"
	Released Kind = "released"
	// TaskFailed is published for a task failed because its server died.
	TaskFailed Kind = "task-failed"
	// Checked is published by the crowd after it checked what an agent remembers.
	Checked Kind = "checked"
)

// Event is something a server or the crowd did.
type Event struct {
	Time    time.Time `json:"time"`
	Kind    Kind      `json:"kind"`
	Server  string    `json:"server,omitempty"`
	Shard   int       `json:"shard"`
	Context string    `json:"context,omitempty"`
	Task    string    `json:"task,omitempty"`
	// User is the "user" metadata of the request, set by the crowd.
	User string `json:"user,omitempty"`
	// Text is the start of the user's message.
	Text string `json:"text,omitempty"`
	// Owner is the server a message was routed to.
	Owner string `json:"owner,omitempty"`
	// From is the previous owner of a claimed shard.
	From     string `json:"from,omitempty"`
	Orphaned bool   `json:"orphaned,omitempty"`
	// Conversations is the number of conversations in a moved shard.
	Conversations int `json:"conversations,omitempty"`
	// Uploaded is what saving the conversation after a turn uploaded, and
	// Size the size of the files it saved.
	Uploaded int64 `json:"uploaded,omitempty"`
	Size     int64 `json:"size,omitempty"`
	// Check names what the crowd checked, and OK whether the agent passed.
	Check string `json:"check,omitempty"`
	OK    bool   `json:"ok,omitempty"`
}

// Publisher publishes events. A nil Publisher drops them.
type Publisher struct {
	nc     *nats.Conn
	server string
}

// NewPublisher returns a publisher of the server's events.
func NewPublisher(nc *nats.Conn, server string) *Publisher {
	return &Publisher{nc: nc, server: server}
}

// Publish publishes e, setting its time and, if empty, its server.
func (p *Publisher) Publish(ctx context.Context, e Event) {
	if p == nil {
		return
	}
	e.Time = time.Now()
	if e.Server == "" {
		e.Server = p.server
	}
	data, err := json.Marshal(e)
	if err != nil {
		log.Warn(ctx, "encoding an event failed", "kind", e.Kind, "cause", err)
		return
	}
	if err := p.nc.Publish(Subject+"."+string(e.Kind), data); err != nil {
		log.Warn(ctx, "publishing an event failed", "kind", e.Kind, "cause", err)
	}
}

// Snippet returns the start of the text of msg.
func Snippet(msg *a2a.Message) string {
	if msg == nil {
		return ""
	}
	var sb strings.Builder
	for _, p := range msg.Parts {
		sb.WriteString(p.Text())
	}
	text := strings.Join(strings.Fields(sb.String()), " ")
	if r := []rune(text); len(r) > snippetLen {
		return string(r[:snippetLen-1]) + "…"
	}
	return text
}
