// Package router sends every payload of a conversation to the server that
// owns the conversation's shard. It is the Writer of a push work queue.
package router

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/workqueue"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/agents"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/nodes"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/mysql/store"
	"github.com/nats-io/nats.go"
)

const (
	subjectPrefix  = "fleet.work."
	forwardTimeout = 5 * time.Second
	pollInterval   = 200 * time.Millisecond
	replyAccepted  = "accepted"
	replyMoved     = "moved"
)

var errMoved = errors.New("the shard moved while the payload was forwarded")

// Config configures a [Router].
type Config struct {
	NATS   *nats.Conn
	Nodes  *nodes.Registry
	Table  *shards.Table
	Shards *shards.Manager
	Agents *agents.Agents
	Index  *store.Index
	// Handle runs a payload on this server, see [workqueue.NewPushQueue].
	Handle workqueue.HandlerFn
	// Wait is how long a payload waits for its shard to get an owner.
	Wait time.Duration
}

// Router routes payloads to the owners of their shards.
type Router struct {
	cfg Config
}

// New returns a router. Call [Router.Serve] to receive payloads forwarded by other servers.
func New(cfg Config) *Router { return &Router{cfg: cfg} }

// Serve receives payloads that other servers forward to this one until ctx ends.
func (r *Router) Serve(ctx context.Context) error {
	sub, err := r.cfg.NATS.Subscribe(subjectPrefix+r.cfg.Nodes.Self().Name, func(msg *nats.Msg) {
		var p workqueue.Payload
		reply := replyAccepted
		if err := json.Unmarshal(msg.Data, &p); err != nil {
			reply = "invalid payload: " + err.Error()
		} else if contextID, err := r.conversation(ctx, &p); err != nil {
			reply = err.Error()
		} else if !r.local(ctx, contextID, &p) {
			reply = replyMoved
		}
		if err := msg.Respond([]byte(reply)); err != nil {
			log.Warn(ctx, "replying to a forwarded payload failed", "task", p.TaskID, "cause", err)
		}
	})
	if err != nil {
		return err
	}
	<-ctx.Done()
	return sub.Unsubscribe()
}

// Write implements [workqueue.Writer]. It returns once the owner accepted
// the payload, so a payload runs at most once.
func (r *Router) Write(ctx context.Context, p *workqueue.Payload) (a2a.TaskID, error) {
	contextID, err := r.conversation(ctx, p)
	if err != nil {
		return "", err
	}
	shard := r.cfg.Shards.Of(contextID)
	deadline := time.Now().Add(r.cfg.Wait)
	for {
		if r.local(ctx, contextID, p) {
			return p.TaskID, nil
		}
		rec := r.cfg.Table.Get(shard)
		self := r.cfg.Nodes.Self()
		if rec.Owner != "" && rec.Owner != self.Name && r.cfg.Nodes.Alive(rec.Owner, rec.Incarnation) {
			err := r.forward(ctx, rec.Owner, p)
			if err == nil {
				log.Info(ctx, "routed", "task", p.TaskID, "context", contextID, "shard", shard, "owner", rec.Owner)
				return p.TaskID, nil
			}
			if !errors.Is(err, errMoved) && !errors.Is(err, nats.ErrNoResponders) {
				return "", err
			}
		}
		if time.Now().After(deadline) {
			return "", fmt.Errorf("shard %d of the conversation has no owner yet, send the message again later", shard)
		}
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		case <-time.After(pollInterval):
		}
	}
}

// conversation returns the context ID of the payload, giving a new conversation one.
func (r *Router) conversation(ctx context.Context, p *workqueue.Payload) (string, error) {
	if p.Type == workqueue.PayloadTypeExecute && p.ExecuteRequest != nil && p.ExecuteRequest.Message != nil {
		msg := p.ExecuteRequest.Message
		if msg.TaskID == "" {
			if msg.ContextID == "" {
				msg.ContextID = a2a.NewContextID()
			}
			return msg.ContextID, nil
		}
	}
	indexed, err := r.cfg.Index.QueryByID(ctx, []a2a.TaskID{p.TaskID})
	if err != nil {
		return "", err
	}
	if len(indexed) == 0 {
		return "", a2a.ErrTaskNotFound
	}
	return indexed[0].ContextID, nil
}

// local runs the payload here if this server owns its shard, and reports whether it did.
func (r *Router) local(ctx context.Context, contextID string, p *workqueue.Payload) bool {
	shard := r.cfg.Shards.Of(contextID)
	if !r.cfg.Shards.Holds(shard) {
		return false
	}
	return r.cfg.Agents.Dispatch(shard, p.TaskID, func() {
		if _, err := r.cfg.Handle(context.WithoutCancel(ctx), p); err != nil {
			log.Warn(ctx, "executing a payload failed", "task", p.TaskID, "type", p.Type, "cause", err)
		}
	})
}

func (r *Router) forward(ctx context.Context, owner string, p *workqueue.Payload) error {
	data, err := json.Marshal(p)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(ctx, forwardTimeout)
	defer cancel()
	msg, err := r.cfg.NATS.RequestWithContext(ctx, subjectPrefix+owner, data)
	if err != nil {
		return fmt.Errorf("forwarding to %s: %w", owner, err)
	}
	switch reply := string(msg.Data); reply {
	case replyAccepted:
		return nil
	case replyMoved:
		return errMoved
	default:
		return fmt.Errorf("%s refused the payload: %s", owner, reply)
	}
}
