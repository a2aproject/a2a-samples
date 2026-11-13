// Package agents runs the ACP agents of the shards this server owns: it
// starts them in their shard's directories, saves their homes after every
// turn, and stops them when their shard moves.
package agents

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/integrations/executor/a2aacp"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
)

// ScratchLostFile is written to a scratch directory that was lost because its
// conversation moved after its server died.
const ScratchLostFile = "SCRATCH_LOST.txt"

// Config configures [Agents].
type Config struct {
	// Server is this server's name, passed to agents as $SERVER.
	Server string
	// Argv is the command of the ACP agent.
	Argv []string
	// MCP is the command of the scratch MCP server; the scratch directory is appended.
	MCP []string
	// ReleaseWait is how long a moving shard waits for turns in progress to end.
	ReleaseWait time.Duration
	// Events publishes agent and turn events; nil drops them.
	Events *events.Publisher
}

// Agents runs the agents of this server's shards.
type Agents struct {
	cfg    Config
	shards *shards.Manager

	mu        sync.Mutex
	changed   *sync.Cond
	running   map[string]int        // context ID -> shard of a running agent
	closers   map[string]io.Closer  // context ID -> stdio of a running agent
	turns     map[a2a.TaskID]string // task ID -> context ID of a turn in progress
	inflight  map[int]int           // shard -> payloads this server is executing
	releasing map[int]bool
}

// New returns the agents of the shards that m owns.
func New(cfg Config, m *shards.Manager) *Agents {
	a := &Agents{
		cfg:       cfg,
		shards:    m,
		running:   map[string]int{},
		closers:   map[string]io.Closer{},
		turns:     map[a2a.TaskID]string{},
		inflight:  map[int]int{},
		releasing: map[int]bool{},
	}
	a.changed = sync.NewCond(&a.mu)
	return a
}

// Start implements [a2aacp.Agent]. The key is the context ID.
func (a *Agents) Start(ctx context.Context, contextID string) (io.ReadWriteCloser, error) {
	n := a.shards.Of(contextID)
	sh, ok := a.shards.Shard(n)
	if !ok {
		return nil, fmt.Errorf("%w: shard %d isn't on %s", a2aacp.ErrNotOwner, n, a.cfg.Server)
	}
	scratchLost, err := sh.Prepare(ctx, contextID)
	if err != nil {
		return nil, err
	}
	home, scratch := sh.HomeDir(contextID), sh.ScratchDir(contextID)
	if scratchLost {
		note := fmt.Sprintf("The scratch directory was lost when this conversation moved to %s after its previous server stopped.\n", a.cfg.Server)
		if err := os.WriteFile(filepath.Join(scratch, ScratchLostFile), []byte(note), 0o600); err != nil {
			return nil, err
		}
	}
	proc := a2aacp.Process{Argv: a.cfg.Argv, Dir: scratch, Env: []string{"HOME=" + home, "SERVER=" + a.cfg.Server}, Stderr: os.Stderr}
	rwc, err := proc.Start(ctx, contextID)
	if err != nil {
		return nil, err
	}
	log.Info(ctx, "started agent", "context", contextID, "shard", n, "epoch", sh.Epoch(), "scratch_lost", scratchLost)
	a.cfg.Events.Publish(ctx, events.Event{Kind: events.AgentStarted, Shard: n, Context: contextID})
	wrapped := a2aacp.WithCleanup(rwc, func() error {
		defer a.stopped(contextID, n)
		_, err := sh.Save(context.Background(), contextID)
		if errors.Is(err, shards.ErrLost) {
			return nil
		}
		return err
	})
	a.mu.Lock()
	a.running[contextID] = n
	a.closers[contextID] = wrapped
	a.mu.Unlock()
	return wrapped, nil
}

func (a *Agents) stopped(contextID string, shard int) {
	a.cfg.Events.Publish(context.Background(), events.Event{Kind: events.AgentStopped, Shard: shard, Context: contextID})
	a.mu.Lock()
	defer a.mu.Unlock()
	delete(a.running, contextID)
	delete(a.closers, contextID)
	a.changed.Broadcast()
}

// Session implements a2aacp Config.Session: the session works in the
// conversation's scratch directory and gets the scratch MCP server.
func (a *Agents) Session(_ context.Context, execCtx *a2asrv.ExecutorContext) (a2aacp.SessionParams, error) {
	n := a.shards.Of(execCtx.ContextID)
	sh, ok := a.shards.Shard(n)
	if !ok {
		return a2aacp.SessionParams{}, fmt.Errorf("%w: shard %d isn't on %s", a2aacp.ErrNotOwner, n, a.cfg.Server)
	}
	scratch := sh.ScratchDir(execCtx.ContextID)
	params := a2aacp.SessionParams{Cwd: scratch}
	if len(a.cfg.MCP) > 0 {
		server, err := json.Marshal(map[string]any{
			"name":    "scratch",
			"command": a.cfg.MCP[0],
			"args":    append(append([]string{}, a.cfg.MCP[1:]...), scratch),
			"env":     []any{},
		})
		if err != nil {
			return a2aacp.SessionParams{}, err
		}
		params.MCPServers = []json.RawMessage{server}
	}
	return params, nil
}

// Turn implements a2aacp Config.Turn: it saves the home and the scratch
// directory when the turn ends.
func (a *Agents) Turn(ctx context.Context, execCtx *a2asrv.ExecutorContext) func() {
	a.mu.Lock()
	a.turns[execCtx.TaskID] = execCtx.ContextID
	a.mu.Unlock()
	n := a.shards.Of(execCtx.ContextID)
	turn := events.Event{Shard: n, Context: execCtx.ContextID, Task: string(execCtx.TaskID)}
	started := turn
	started.Kind, started.Text = events.TurnStarted, events.Snippet(execCtx.Message)
	a.cfg.Events.Publish(ctx, started)
	return func() {
		defer func() {
			a.mu.Lock()
			delete(a.turns, execCtx.TaskID)
			a.changed.Broadcast()
			a.mu.Unlock()
		}()
		ended := turn
		ended.Kind = events.TurnEnded
		defer func() { a.cfg.Events.Publish(ctx, ended) }()
		sh, ok := a.shards.Shard(n)
		if !ok {
			return
		}
		saved, err := sh.Save(ctx, execCtx.ContextID)
		if err != nil {
			log.Warn(ctx, "saving the conversation failed", "context", execCtx.ContextID, "cause", err)
			return
		}
		ended.Uploaded, ended.Size = saved.Uploaded, saved.Size
		if !saved.ScratchSaved {
			log.Info(ctx, "scratch is over the limit, it moves only with a graceful release", "context", execCtx.ContextID)
		}
	}
}

// Dispatch runs a payload of the shard on this server unless the shard is
// moving and the payload isn't for a turn in progress here. It reports whether it ran.
func (a *Agents) Dispatch(shard int, taskID a2a.TaskID, run func()) bool {
	a.mu.Lock()
	_, inTurn := a.turns[taskID]
	if a.releasing[shard] && !inTurn {
		a.mu.Unlock()
		return false
	}
	a.inflight[shard]++
	a.mu.Unlock()
	go func() {
		defer func() {
			a.mu.Lock()
			a.inflight[shard]--
			a.changed.Broadcast()
			a.mu.Unlock()
		}()
		run()
	}()
	return true
}

// Release implements [shards.Agents]. It waits up to ReleaseWait for the
// shard's turns and payloads to end, then stops its agents, which saves their homes.
func (a *Agents) Release(ctx context.Context, shard int) {
	deadline := time.Now().Add(a.cfg.ReleaseWait)
	wake := time.AfterFunc(a.cfg.ReleaseWait, func() {
		a.mu.Lock()
		a.changed.Broadcast()
		a.mu.Unlock()
	})
	defer wake.Stop()

	a.mu.Lock()
	a.releasing[shard] = true
	for !a.idleLocked(shard) && time.Now().Before(deadline) {
		a.changed.Wait()
	}
	if !a.idleLocked(shard) {
		log.Warn(ctx, "turns still running when the shard moves, they are canceled", "shard", shard)
	}
	var closers []io.Closer
	for c, n := range a.running {
		if n == shard {
			closers = append(closers, a.closers[c])
		}
	}
	a.mu.Unlock()

	for _, c := range closers {
		if err := c.Close(); err != nil {
			log.Warn(ctx, "stopping an agent failed", "shard", shard, "cause", err)
		}
	}
	a.mu.Lock()
	for a.runningLocked(shard) {
		a.changed.Wait()
	}
	delete(a.releasing, shard)
	a.mu.Unlock()
}

func (a *Agents) idleLocked(shard int) bool {
	if a.inflight[shard] > 0 {
		return false
	}
	for _, c := range a.turns {
		if a.shards.Of(c) == shard {
			return false
		}
	}
	return true
}

func (a *Agents) runningLocked(shard int) bool {
	for _, n := range a.running {
		if n == shard {
			return true
		}
	}
	return false
}

// Sessions returns the [a2aacp.SessionStore] backed by the shards' SQLite session maps.
func (a *Agents) Sessions() a2aacp.SessionStore { return sessionStore{a} }

type sessionStore struct{ a *Agents }

func (s sessionStore) Get(ctx context.Context, contextID string) (a2aacp.Session, bool, error) {
	sh, err := s.shard(contextID)
	if err != nil {
		return a2aacp.Session{}, false, err
	}
	id, agentKey, ok, err := sh.Session(ctx, contextID)
	return a2aacp.Session{ID: id, AgentKey: agentKey}, ok, err
}

func (s sessionStore) Put(ctx context.Context, contextID string, sess a2aacp.Session) error {
	sh, err := s.shard(contextID)
	if err != nil {
		return err
	}
	return sh.PutSession(ctx, contextID, sess.ID, sess.AgentKey)
}

func (s sessionStore) shard(contextID string) (*shards.Shard, error) {
	n := s.a.shards.Of(contextID)
	sh, ok := s.a.shards.Shard(n)
	if !ok {
		return nil, fmt.Errorf("%w: shard %d isn't on %s", a2aacp.ErrNotOwner, n, s.a.cfg.Server)
	}
	return sh, nil
}
