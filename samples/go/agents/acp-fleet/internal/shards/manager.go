package shards

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"sync"
	"time"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/nodes"
)

// DefaultLimit is the default size limit of a snapshot.
const DefaultLimit = 64 << 20

// DefaultScratchLimit is the default size limit of the scratch snapshots
// taken after every turn.
const DefaultScratchLimit = 16 << 20

// Agents stops the agents of a shard before it moves.
type Agents interface {
	// Release stops the agents of the shard, waiting for their turns to end
	// for a while, and returns once all of them are stopped.
	Release(ctx context.Context, shard int)
}

// Config configures a [Manager].
type Config struct {
	// Count is the number of shards. All servers must use the same count.
	Count int
	// Dir is the local directory of the shards this server owns.
	Dir string
	// Limit is the size limit of a snapshot, [DefaultLimit] if zero.
	Limit int64
	// ScratchLimit is the size limit of the scratch snapshots taken after
	// every turn, [DefaultScratchLimit] if zero. Larger scratch directories
	// move only when their shard moves gracefully.
	ScratchLimit int64
	// Orphaned is called after this server takes a shard over from a server
	// that died, to fail the tasks that server was working on.
	Orphaned func(ctx context.Context, shard int)
	// Events publishes shard moves; nil drops them.
	Events *events.Publisher
}

// Manager claims the shards that rendezvous hashing assigns to this server
// and releases the others.
type Manager struct {
	cfg   Config
	table *Table
	nodes *nodes.Registry

	mu        sync.Mutex
	owned     map[int]*Shard
	releasing map[int]bool
	changed   chan struct{}
}

// NewManager returns a manager of the shards in table for this server of nodes.
func NewManager(cfg Config, table *Table, nodes *nodes.Registry) *Manager {
	if cfg.Limit == 0 {
		cfg.Limit = DefaultLimit
	}
	if cfg.ScratchLimit == 0 {
		cfg.ScratchLimit = DefaultScratchLimit
	}
	return &Manager{cfg: cfg, table: table, nodes: nodes, owned: map[int]*Shard{}, releasing: map[int]bool{}, changed: make(chan struct{}, 1)}
}

// Count returns the number of shards.
func (m *Manager) Count() int { return m.cfg.Count }

// Of returns the shard of a conversation.
func (m *Manager) Of(contextID string) int { return Of(contextID, m.cfg.Count) }

// Shard returns the shard if this server owns it and isn't releasing it.
func (m *Manager) Shard(n int) (*Shard, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	s, ok := m.owned[n]
	if !ok || m.releasing[n] || s.isLost() {
		return nil, false
	}
	return s, true
}

// Holds reports whether this server owns the shard, including while it releases it.
func (m *Manager) Holds(n int) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	s, ok := m.owned[n]
	return ok && !s.isLost()
}

// Owned returns the shards this server owns, including those it is releasing.
func (m *Manager) Owned() []int {
	m.mu.Lock()
	defer m.mu.Unlock()
	var ids []int
	for id := range m.owned {
		ids = append(ids, id)
	}
	slices.Sort(ids)
	return ids
}

// Changed returns a channel that receives a value after this server claims or releases a shard.
func (m *Manager) Changed() <-chan struct{} { return m.changed }

// Run claims and releases shards until ctx ends. A draining server releases all of them.
func (m *Manager) Run(ctx context.Context, agents Agents) error {
	if err := os.MkdirAll(m.cfg.Dir, 0o700); err != nil {
		return err
	}
	nodeChanges, recordChanges := m.nodes.Subscribe(), m.table.Subscribe()
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	releases := make(chan int, m.cfg.Count)
	var wg sync.WaitGroup
	wg.Go(func() {
		for n := range releases {
			m.release(context.WithoutCancel(ctx), agents, n)
		}
	})
	defer func() {
		close(releases)
		wg.Wait()
	}()
	for {
		m.reconcile(ctx, agents, releases)
		select {
		case <-ctx.Done():
			return nil
		case <-nodeChanges:
		case <-recordChanges:
		case <-ticker.C:
		}
	}
}

func (m *Manager) reconcile(ctx context.Context, agents Agents, releases chan<- int) {
	self := m.nodes.Self()
	var candidates []string
	for _, n := range m.nodes.Live() {
		if !n.Draining {
			candidates = append(candidates, n.Name)
		}
	}
	for n := range m.cfg.Count {
		want := !self.Draining && Assign(n, candidates) == self.Name
		m.mu.Lock()
		s, owned := m.owned[n]
		releasing := m.releasing[n]
		m.mu.Unlock()
		switch {
		case owned && s.isLost() && !releasing:
			log.Warn(ctx, "shard lost", "shard", n)
			agents.Release(ctx, n)
			m.forget(ctx, n, s)
		case want && !owned:
			if err := m.claim(ctx, n); err != nil {
				log.Warn(ctx, "claiming a shard failed", "shard", n, "cause", err)
			}
		case !want && owned && !releasing:
			m.mu.Lock()
			m.releasing[n] = true
			m.mu.Unlock()
			releases <- n
		}
	}
}

func (m *Manager) claim(ctx context.Context, n int) error {
	self := m.nodes.Self()
	rec, rev, err := m.table.load(ctx, n)
	if err != nil {
		return err
	}
	if rec.Owner != "" && m.nodes.Alive(rec.Owner, rec.Incarnation) {
		return nil
	}
	orphaned := rec.Owner != ""
	next := rec.clone()
	next.Owner, next.Incarnation = self.Name, self.Incarnation
	next.Epoch++
	var expired []string
	for c, o := range next.Homes {
		if time.Since(o.Saved) > retention {
			delete(next.Homes, c)
			delete(next.Scratch, c)
			expired = append(expired, c)
		}
	}
	rev, err = m.table.swap(ctx, n, next, rev)
	if err != nil {
		return nil
	}
	s := &Shard{ID: n, dir: filepath.Join(m.cfg.Dir, key(n)), table: m.table, limit: m.cfg.Limit, scratchLimit: m.cfg.ScratchLimit, rec: next, rev: rev}
	s.deleteObjects(ctx, superseded(rec, next))
	if err := s.open(ctx); err != nil {
		return errors.Join(fmt.Errorf("opening shard %d: %w", n, err), s.release(ctx), s.close())
	}
	for _, c := range expired {
		if _, err := s.db.ExecContext(ctx, `DELETE FROM sessions WHERE context_id = ?`, c); err != nil {
			log.Warn(ctx, "forgetting an expired conversation failed", "shard", n, "context", c, "cause", err)
		}
	}
	m.mu.Lock()
	m.owned[n] = s
	m.mu.Unlock()
	log.Info(ctx, "claimed shard", "shard", n, "epoch", next.Epoch, "from", rec.Owner, "orphaned", orphaned, "conversations", len(next.Homes))
	m.cfg.Events.Publish(ctx, events.Event{Kind: events.Claimed, Shard: n, From: rec.Owner, Orphaned: orphaned, Conversations: len(next.Homes)})
	if orphaned && m.cfg.Orphaned != nil {
		m.cfg.Orphaned(ctx, n)
	}
	m.notify()
	return nil
}

func (m *Manager) release(ctx context.Context, agents Agents, n int) {
	start := time.Now()
	agents.Release(ctx, n)
	m.mu.Lock()
	s := m.owned[n]
	m.mu.Unlock()
	if err := s.release(ctx); err != nil {
		log.Warn(ctx, "releasing a shard failed, it moves when this server's heartbeat expires", "shard", n, "cause", err)
	} else {
		log.Info(ctx, "released shard", "shard", n, "took", time.Since(start).Round(time.Millisecond))
		m.cfg.Events.Publish(ctx, events.Event{Kind: events.Released, Shard: n})
	}
	m.forget(ctx, n, s)
}

func (m *Manager) forget(ctx context.Context, n int, s *Shard) {
	if err := s.close(); err != nil {
		log.Warn(ctx, "closing a shard failed", "shard", n, "cause", err)
	}
	m.mu.Lock()
	delete(m.owned, n)
	delete(m.releasing, n)
	m.mu.Unlock()
	m.notify()
}

func (m *Manager) notify() {
	select {
	case m.changed <- struct{}{}:
	default:
	}
}
