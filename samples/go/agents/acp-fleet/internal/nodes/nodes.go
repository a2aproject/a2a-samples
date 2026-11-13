// Package nodes tracks the live servers of the fleet with heartbeats in the
// NODES KV bucket. A record expires when its server stops writing it, and the
// bucket's TTL markers tell every watcher at once.
package nodes

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"sync"
	"time"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/nats-io/nats.go/jetstream"
)

const bucket = "NODES"

// Node is a live server.
type Node struct {
	Name string `json:"name"`
	// Incarnation is random for every start of the server, so that records
	// written by an earlier process of the same name can be told apart.
	Incarnation string `json:"incarnation"`
	Draining    bool   `json:"draining"`
}

// Config configures a [Registry].
type Config struct {
	Name string
	// Heartbeat is how often the server rewrites its record.
	Heartbeat time.Duration
	// TTL is how long a record lives after its last write.
	TTL time.Duration
	// OnLost is called when the server couldn't write its record for
	// TTL - 2 * Heartbeat, so it must stop its agents before others take
	// over its shards.
	OnLost func()
}

// Registry is this server's membership in the fleet and its view of the others.
type Registry struct {
	cfg  Config
	kv   jetstream.KeyValue
	self Node

	mu    sync.Mutex
	nodes map[string]Node
	subs  []chan struct{}
}

// Join creates the NODES bucket if needed, writes this server's record and
// keeps it fresh until ctx ends.
func Join(ctx context.Context, js jetstream.JetStream, cfg Config) (*Registry, error) {
	kv, err := js.CreateOrUpdateKeyValue(ctx, jetstream.KeyValueConfig{
		Bucket:         bucket,
		TTL:            cfg.TTL,
		LimitMarkerTTL: max(cfg.TTL, time.Second),
		Storage:        jetstream.MemoryStorage,
	})
	if err != nil {
		return nil, fmt.Errorf("creating the %s bucket: %w", bucket, err)
	}
	r := &Registry{cfg: cfg, kv: kv, self: Node{Name: cfg.Name, Incarnation: randomID()}, nodes: map[string]Node{}}
	if err := r.write(ctx); err != nil {
		return nil, err
	}
	watcher, err := kv.WatchAll(ctx)
	if err != nil {
		return nil, fmt.Errorf("watching the %s bucket: %w", bucket, err)
	}
	go r.watch(ctx, watcher)
	go r.heartbeat(ctx)
	return r, nil
}

// Self returns this server's record.
func (r *Registry) Self() Node {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.self
}

// Live returns the live servers sorted by name.
func (r *Registry) Live() []Node {
	r.mu.Lock()
	defer r.mu.Unlock()
	nodes := make([]Node, 0, len(r.nodes))
	for _, n := range r.nodes {
		nodes = append(nodes, n)
	}
	slices.SortFunc(nodes, func(a, b Node) int {
		switch {
		case a.Name < b.Name:
			return -1
		case a.Name > b.Name:
			return 1
		}
		return 0
	})
	return nodes
}

// Alive reports whether the server of the name runs with the incarnation.
func (r *Registry) Alive(name, incarnation string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	n, ok := r.nodes[name]
	return ok && n.Incarnation == incarnation
}

// Subscribe returns a channel that receives a value after the live servers change.
func (r *Registry) Subscribe() <-chan struct{} {
	ch := make(chan struct{}, 1)
	r.mu.Lock()
	r.subs = append(r.subs, ch)
	r.mu.Unlock()
	return ch
}

// SetDraining marks this server draining, so that its shards move to other servers.
func (r *Registry) SetDraining(ctx context.Context) error {
	r.mu.Lock()
	r.self.Draining = true
	r.mu.Unlock()
	return r.write(ctx)
}

// Leave deletes this server's record.
func (r *Registry) Leave(ctx context.Context) error {
	return r.kv.Delete(ctx, r.cfg.Name)
}

func (r *Registry) write(ctx context.Context) error {
	data, err := json.Marshal(r.Self())
	if err != nil {
		return err
	}
	if _, err := r.kv.Put(ctx, r.cfg.Name, data); err != nil {
		return fmt.Errorf("writing the record of %s: %w", r.cfg.Name, err)
	}
	return nil
}

func (r *Registry) heartbeat(ctx context.Context) {
	ticker := time.NewTicker(r.cfg.Heartbeat)
	defer ticker.Stop()
	lastWrite := time.Now()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
		err := r.write(ctx)
		if err == nil {
			lastWrite = time.Now()
			continue
		}
		if errors.Is(err, context.Canceled) {
			return
		}
		log.Warn(ctx, "heartbeat failed", "cause", err)
		if time.Since(lastWrite) > r.cfg.TTL-2*r.cfg.Heartbeat && r.cfg.OnLost != nil {
			r.cfg.OnLost()
			return
		}
	}
}

func (r *Registry) watch(ctx context.Context, w jetstream.KeyWatcher) {
	defer func() {
		if err := w.Stop(); err != nil && ctx.Err() == nil {
			log.Warn(ctx, "stopping the nodes watcher failed", "cause", err)
		}
	}()
	for {
		select {
		case <-ctx.Done():
			return
		case e, ok := <-w.Updates():
			if !ok {
				return
			}
			if e == nil {
				continue
			}
			r.apply(ctx, e)
		}
	}
}

func (r *Registry) apply(ctx context.Context, e jetstream.KeyValueEntry) {
	r.mu.Lock()
	defer r.mu.Unlock()
	switch e.Operation() {
	case jetstream.KeyValueDelete, jetstream.KeyValuePurge:
		if _, ok := r.nodes[e.Key()]; ok {
			log.Info(ctx, "server left", "server", e.Key())
		}
		delete(r.nodes, e.Key())
	default:
		var n Node
		if err := json.Unmarshal(e.Value(), &n); err != nil {
			log.Warn(ctx, "invalid node record", "key", e.Key(), "cause", err)
			return
		}
		if old, ok := r.nodes[n.Name]; ok && old == n {
			return
		}
		log.Info(ctx, "server joined or changed", "server", n.Name, "incarnation", n.Incarnation, "draining", n.Draining)
		r.nodes[n.Name] = n
	}
	for _, ch := range r.subs {
		select {
		case ch <- struct{}{}:
		default:
		}
	}
}

func randomID() string {
	b := make([]byte, 4)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b)
}
