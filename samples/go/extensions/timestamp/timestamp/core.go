package timestamp

import (
	"context"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
)

const (
	_CorePath      = "github.com/a2aproject/a2a-samples/extensions/timestamp/v1"
	URI            = "https://" + _CorePath
	TimestampField = _CorePath + "/timestamp"
)

// Option specifies configuration options for TimestampExtension.
type Option func(*TimestampExtension)

// WithClock sets a custom clock function for timestamp generation.
func WithClock(nowFn func() time.Time) Option {
	return func(e *TimestampExtension) {
		if nowFn != nil {
			e.nowFn = nowFn
		}
	}
}

// TimestampExtension is an implementation of the Timestamp extension.
type TimestampExtension struct {
	nowFn          func() time.Time
	agentExtension a2a.AgentExtension
}

// NewTimestampExtension creates a new TimestampExtension instance.
func NewTimestampExtension(opts ...Option) *TimestampExtension {
	ext := &TimestampExtension{
		nowFn: time.Now,
		agentExtension: a2a.AgentExtension{
			URI:         URI,
			Description: "Adds timestamps to messages and artifacts.",
		},
	}
	for _, opt := range opts {
		opt(ext)
	}
	return ext
}

// AddToCard adds this extension to an AgentCard.
func (e *TimestampExtension) AddToCard(card *a2a.AgentCard) *a2a.AgentCard {
	card.Capabilities.Extensions = append(card.Capabilities.Extensions, e.agentExtension)
	return card
}

// IsSupported returns whether this extension is supported by the AgentCard.
func (e *TimestampExtension) IsSupported(card *a2a.AgentCard) bool {
	if card == nil {
		return false
	}
	for _, ext := range card.Capabilities.Extensions {
		if ext.URI == URI {
			return true
		}
	}
	return false
}

// IsRequested returns whether the client requested this extension for the call.
//
// The extension is considered requested if the caller indicated it in
// an A2A-Extensions header.
func (e *TimestampExtension) IsRequested(ctx context.Context) bool {
	if ext, ok := a2asrv.ExtensionsFrom(ctx); ok {
		return ext.Requested(&e.agentExtension)
	}
	return false
}

// ApplyTimestamp adds a timestamp to a message or artifact.
func (e *TimestampExtension) ApplyTimestamp(o a2a.MetadataCarrier) {
	// Respect existing timestamps.
	if e.HasTimestamp(o) {
		return
	}
	now := e.nowFn().UTC()
	o.SetMeta(TimestampField, now.Format(time.RFC3339Nano))
}

// TimestampEvent adds a timestamp to a server-side event.
func (e *TimestampExtension) TimestampEvent(event a2a.Event) {
	for _, o := range e.getMessagesInEvent(event) {
		e.ApplyTimestamp(o)
	}
}

// HasTimestamp returns whether a message or artifact has a timestamp.
func (e *TimestampExtension) HasTimestamp(o a2a.MetadataCarrier) bool {
	if o == nil || o.Meta() == nil {
		return false
	}
	_, exists := o.Meta()[TimestampField]
	return exists
}

func (e *TimestampExtension) getMessagesInEvent(event a2a.Event) []a2a.MetadataCarrier {
	switch v := event.(type) {
	case *a2a.TaskStatusUpdateEvent:
		if v.Status.Message != nil {
			return []a2a.MetadataCarrier{v.Status.Message}
		}
	case *a2a.TaskArtifactUpdateEvent:
		if v.Artifact != nil {
			return []a2a.MetadataCarrier{v.Artifact}
		}
	case *a2a.Message:
		return []a2a.MetadataCarrier{v}
	case *a2a.Task:
		return e.getArtifactsAndMessagesInTask(v)
	}
	return nil
}

func (e *TimestampExtension) getArtifactsAndMessagesInTask(t *a2a.Task) []a2a.MetadataCarrier {
	var result []a2a.MetadataCarrier
	for _, a := range t.Artifacts {
		result = append(result, a)
	}
	for _, m := range t.History {
		if m.Role == a2a.MessageRoleAgent {
			result = append(result, m)
		}
	}
	if t.Status.Message != nil {
		result = append(result, t.Status.Message)
	}
	return result
}
