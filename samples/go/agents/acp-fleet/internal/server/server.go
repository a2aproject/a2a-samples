// Package server wires a fleet server: the task store and event queues of the
// integrations, the shards, the ACP agents and the router.
package server

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net"
	"net/http"
	"path/filepath"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aext/structuredinput"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/a2asrv/workqueue"
	"github.com/a2aproject/a2a-go/v2/integrations/executor/a2aacp"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/agents"
	fleetevents "github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/nodes"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/router"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/tasks"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/mysql/store"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/nats/lease"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/nats/msgstream"
	_ "github.com/go-sql-driver/mysql" // MySQL driver registration
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

const partition = "acp-fleet"

// Config configures a server.
type Config struct {
	Name       string
	ListenAddr string
	// PublicURL is the URL clients reach the fleet at, the load balancer's.
	PublicURL string
	NATSURL   string
	MySQLDSN  string
	// DataDir holds the shards this server owns.
	DataDir string
	// AgentCommand is the command of the ACP agent.
	AgentCommand []string
	// MCPCommand is the command of the scratch MCP server.
	MCPCommand []string
	Shards     int
	// ScratchLimit caps the scratch snapshots taken after every turn.
	ScratchLimit int64
	// IdleTimeout stops agents with no turns for this long.
	IdleTimeout time.Duration
	// DrainTimeout bounds how long a moving shard waits for turns to end.
	DrainTimeout   time.Duration
	MaxAgents      int
	OutboxInterval time.Duration
	Heartbeat      time.Duration
	HeartbeatTTL   time.Duration
	// OnLost is called when this server lost its membership and must stop.
	OnLost func()
}

// Server is a running fleet server.
type Server struct {
	// Addr is the address the server listens on.
	Addr string

	cfg      Config
	nodes    *nodes.Registry
	shards   *shards.Manager
	exec     *a2aacp.Executor
	http     *http.Server
	stop     context.CancelFunc
	managers chan error
	closers  []func() error
}

// Start connects to NATS and MySQL, joins the fleet and serves A2A until [Server.Shutdown].
func Start(ctx context.Context, cfg Config) (*Server, error) {
	ctx, stop := context.WithCancel(ctx)
	s := &Server{cfg: cfg, stop: stop, managers: make(chan error, 1)}
	if err := s.start(ctx); err != nil {
		stop()
		return nil, errors.Join(err, s.closeAll())
	}
	return s, nil
}

func (s *Server) start(ctx context.Context) error {
	cfg := s.cfg
	db, err := sql.Open("mysql", cfg.MySQLDSN)
	if err != nil {
		return err
	}
	s.closers = append(s.closers, db.Close)
	nc, err := nats.Connect(cfg.NATSURL, nats.Name(cfg.Name))
	if err != nil {
		return fmt.Errorf("connecting to NATS: %w", err)
	}
	s.closers = append(s.closers, func() error { nc.Close(); return nil })
	js, err := jetstream.New(nc)
	if err != nil {
		return err
	}

	if _, err := js.CreateOrUpdateStream(ctx, jetstream.StreamConfig{
		Name:     "EVENTS",
		Subjects: []string{"events.>"},
		MaxAge:   7 * 24 * time.Hour,
		Storage:  jetstream.FileStorage,
	}); err != nil {
		return fmt.Errorf("creating the EVENTS stream: %w", err)
	}
	leader, err := lease.CreateManager(ctx, js, jetstream.KeyValueConfig{Bucket: "OUTBOX", TTL: 3*cfg.OutboxInterval + time.Second})
	if err != nil {
		return err
	}
	outbox, err := store.NewOutbox(store.OutboxConfig{DB: db, Partition: partition, Writer: msgstream.NewEventWriter(js), Leader: leader, Interval: cfg.OutboxInterval})
	if err != nil {
		return err
	}
	go func() {
		if err := outbox.Run(ctx); err != nil && !errors.Is(err, context.Canceled) {
			log.Error(ctx, "outbox stopped", err)
		}
	}()
	events, err := msgstream.CreateEventQueueManager(ctx, js)
	if err != nil {
		return err
	}
	replay, err := msgstream.CreateEventReplayManager(ctx, js)
	if err != nil {
		return err
	}
	index := store.NewIndex(db, partition)
	taskStore := store.New(store.Config{DB: db, Outbox: outbox, TaskIndex: index, EventReplay: replay})

	s.nodes, err = nodes.Join(ctx, js, nodes.Config{Name: cfg.Name, Heartbeat: cfg.Heartbeat, TTL: cfg.HeartbeatTTL, OnLost: cfg.OnLost})
	if err != nil {
		return err
	}
	table, err := shards.OpenTable(ctx, js)
	if err != nil {
		return err
	}
	pub := fleetevents.NewPublisher(nc, cfg.Name)
	failer := tasks.NewFailer(taskStore, index, cfg.Shards, pub)
	s.shards = shards.NewManager(shards.Config{Count: cfg.Shards, Dir: filepath.Join(cfg.DataDir, "shards"), ScratchLimit: cfg.ScratchLimit, Orphaned: failer.Orphaned, Events: pub}, table, s.nodes)
	fleetAgents := agents.New(agents.Config{Server: cfg.Name, Argv: cfg.AgentCommand, MCP: cfg.MCPCommand, ReleaseWait: cfg.DrainTimeout, Events: pub}, s.shards)

	s.exec, err = a2aacp.NewExecutor(ctx, a2aacp.AgentFunc(fleetAgents.Start), &a2aacp.Config{
		Pool:         &a2aacp.PoolConfig{IdleTimeout: cfg.IdleTimeout, MaxAgents: cfg.MaxAgents},
		SessionStore: fleetAgents.Sessions(),
		Session:      fleetAgents.Session,
		Turn:         fleetAgents.Turn,
		Abandoned:    failer.Abandoned,
	})
	if err != nil {
		return err
	}

	var rt *router.Router
	queue, handle := workqueue.NewPushQueue(workqueue.WriterFunc(func(ctx context.Context, p *workqueue.Payload) (a2a.TaskID, error) {
		return rt.Write(ctx, p)
	}))
	rt = router.New(router.Config{NATS: nc, Nodes: s.nodes, Table: table, Shards: s.shards, Agents: fleetAgents, Index: index, Handle: handle, Wait: cfg.DrainTimeout + cfg.HeartbeatTTL, Events: pub})

	card := &a2a.AgentCard{
		Name:                "ACP fleet",
		Description:         "ACP agents in a2a-go cluster mode, in virtual shards that move between servers.",
		Version:             "1.0.0",
		SupportedInterfaces: []*a2a.AgentInterface{a2a.NewAgentInterface(cfg.PublicURL, a2a.TransportProtocolHTTPJSON)},
		Capabilities:        a2a.AgentCapabilities{Streaming: true, Extensions: []a2a.AgentExtension{structuredinput.NewExtension(structuredinput.DefaultDraft)}},
		DefaultInputModes:   []string{"text/plain"},
		DefaultOutputModes:  []string{"text/plain"},
		Skills:              []a2a.AgentSkill{{ID: "chat", Name: "Chat", Description: "Talk to a coding agent.", Tags: []string{"acp"}}},
	}
	handler := a2asrv.NewHandler(s.exec, a2asrv.WithClusterMode(a2asrv.ClusterConfig{TaskStore: taskStore, QueueManager: events, WorkQueue: queue}))
	mux := http.NewServeMux()
	mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(card))
	mux.Handle("/", a2asrv.NewRESTHandler(handler))

	go func() {
		if err := rt.Serve(ctx); err != nil {
			log.Error(ctx, "router stopped", err)
		}
	}()
	go func() { s.managers <- s.shards.Run(ctx, fleetAgents) }()

	ln, err := net.Listen("tcp", cfg.ListenAddr)
	if err != nil {
		return err
	}
	s.Addr = ln.Addr().String()
	s.http = &http.Server{Handler: mux, ReadHeaderTimeout: 30 * time.Second}
	go func() {
		if err := s.http.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error(ctx, "http server stopped", err)
		}
	}()
	log.Info(ctx, "server started", "server", cfg.Name, "incarnation", s.nodes.Self().Incarnation, "listen", s.Addr)
	return nil
}

// Shutdown drains the server: its shards move to other servers once their
// turns end, then it leaves the fleet. It gives up after ctx ends.
func (s *Server) Shutdown(ctx context.Context) error {
	log.Info(ctx, "drain started", "shards", len(s.shards.Owned()))
	start := time.Now()
	errs := []error{s.nodes.SetDraining(ctx)}
	for len(s.shards.Owned()) > 0 {
		select {
		case <-ctx.Done():
			errs = append(errs, fmt.Errorf("shards still owned after the drain: %v", s.shards.Owned()))
		case <-s.shards.Changed():
			continue
		case <-time.After(time.Second):
			continue
		}
		break
	}
	log.Info(ctx, "drain finished", "took", time.Since(start).Round(time.Millisecond))
	s.stop()
	if err := <-s.managers; err != nil {
		errs = append(errs, err)
	}
	errs = append(errs, s.exec.Shutdown(ctx), s.http.Shutdown(ctx), s.nodes.Leave(context.WithoutCancel(ctx)))
	return errors.Join(append(errs, s.closeAll())...)
}

// Kill stops the server as a crash would, for tests: it disconnects first,
// so its agents stop without saving.
func (s *Server) Kill() error {
	s.stop()
	err := errors.Join(s.http.Close(), s.closeAll())
	if closeErr := s.exec.Close(); closeErr != nil {
		log.Info(context.Background(), "agents stopped without saving", "cause", closeErr)
	}
	return err
}

func (s *Server) closeAll() error {
	var errs []error
	for i := len(s.closers) - 1; i >= 0; i-- {
		errs = append(errs, s.closers[i]())
	}
	s.closers = nil
	return errors.Join(errs...)
}
