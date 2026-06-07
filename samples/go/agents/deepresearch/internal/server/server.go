// Package server wires infrastructure and starts an A2A agent HTTP server.
package server

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/a2asrv/push"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/agents"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/cluster"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/lease"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/msgstream"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/report"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/store"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/utils"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
	"google.golang.org/adk/model"
)

const (
	// DefaultResearcherURL is the default endpoint for the researcher service.
	DefaultResearcherURL = "http://researcher-svc"
	// DefaultAnalyzerURL is the default endpoint for the analyzer service.
	DefaultAnalyzerURL = "http://analyzer-svc"
	// DefaultSynthesizerURL is the default endpoint for the synthesizer service.
	DefaultSynthesizerURL = "http://synthesizer-svc"
)

const defaultOutboxInterval = 3 * time.Second

// Config holds configuration for a single agent server.
type Config struct {
	AgentType domain.AgentType // required
	Model     model.LLM        // required

	ListenAddr     string        // defaults to :8080
	SelfURL        string        // defaults to ListenAddr
	ReportURL      string        // defaults to SelfURL
	NatsURL        string        // defaults to [nats.DefaultURL]
	MySQLDSN       string        // defaults to local DSN
	ResearcherURL  string        // defaults to [DefaultResearcherURL]
	AnalyzerURL    string        // defaults to [DefaultAnalyzerURL]
	SynthesizerURL string        // defaults to [DefaultSynthesizerURL]
	OutboxInterval time.Duration // defaults to [defaultOutboxInterval]
}

// Server is a running agent server.
type Server struct {
	// Addr is the address the server is listening on (host:port).
	Addr string

	close func()
}

// Close releases all resources held by the server.
func (s *Server) Close() { s.close() }

// Start creates and starts a server. Panics on infra connect errors.
func Start(ctx context.Context, cfg Config) *Server {
	listenAddr := or(cfg.ListenAddr, ":8080")
	natsURL := or(cfg.NatsURL, nats.DefaultURL)
	mysqlDSN := or(cfg.MySQLDSN, "root:root@tcp(localhost:3306)/planner?parseTime=true")
	researcherURL := or(cfg.ResearcherURL, DefaultResearcherURL)
	analyzerURL := or(cfg.AnalyzerURL, DefaultAnalyzerURL)
	synthesizerURL := or(cfg.SynthesizerURL, DefaultSynthesizerURL)

	if cfg.Model == nil {
		panic("server: Config.Model is required")
	}

	db := utils.Must(sql.Open("mysql", mysqlDSN))
	log.Info(ctx, "MySQL connected")

	nc := utils.Must(nats.Connect(natsURL))
	js := utils.Must(jetstream.New(nc))
	log.Info(ctx, "NATS connected")

	outboxInterval := cfg.OutboxInterval
	if outboxInterval <= 0 {
		outboxInterval = defaultOutboxInterval
	}
	outbox := utils.Must(store.NewOutbox(store.OutboxConfig{
		DB:       db,
		Agent:    cfg.AgentType,
		Writer:   msgstream.NewEventWriter(js),
		Interval: outboxInterval,
		LeaseManager: utils.Must(lease.CreateManager(ctx, js, jetstream.KeyValueConfig{
			Bucket: "OUTBOX",
			TTL:    outboxInterval*3 + time.Second,
		})),
	}))
	outboxCtx, cancelOutbox := context.WithCancel(ctx)
	go func() {
		if err := outbox.Run(outboxCtx); err != nil {
			log.Error(outboxCtx, "outbox stopped", err)
		}
	}()

	eventQueueManager := utils.Must(msgstream.CreateEventQueueManager(ctx, js))
	eventReplayManager := utils.Must(msgstream.CreateEventReplayManager(ctx, js))

	taskStore := store.New(store.Config{
		DB:          db,
		Outbox:      outbox,
		TaskIndex:   store.NewIndex(db),
		EventReplay: eventReplayManager,
	})
	workQueue := utils.Must(msgstream.CreateWorkQueue(ctx, js, cfg.AgentType))

	ln := utils.Must(net.Listen("tcp", listenAddr))

	selfURL := cfg.SelfURL
	if selfURL == "" {
		selfURL = "http://" + ln.Addr().String()
	}

	var executor a2asrv.AgentExecutor
	switch cfg.AgentType {
	case domain.AgentOrchestrator:
		reportURL := or(cfg.ReportURL, selfURL)
		executor = utils.Must(agents.CreateOrchestrator(ctx, agents.OrchestratorConfig{
			JS:          js,
			ReportStore: a2a.URL(reportURL),
			Researcher:  utils.Must(cluster.CreateClient(ctx, researcherURL)),
			Analyzer:    utils.Must(cluster.CreateClient(ctx, analyzerURL)),
			Synthesizer: utils.Must(cluster.CreateClient(ctx, synthesizerURL)),
			Model:       cfg.Model,
		}))
	case domain.AgentResearcher:
		executor = utils.Must(agents.NewResearcher(cfg.Model))
	case domain.AgentAnalyzer:
		executor = utils.Must(agents.NewAnalyzer(taskStore, cfg.Model))
	case domain.AgentSynthesizer:
		executor = utils.Must(agents.NewSynthesizer(taskStore, cfg.Model))
	default:
		panic(fmt.Sprintf("unknown agent type: %q", cfg.AgentType))
	}

	card := &a2a.AgentCard{
		Name:        string(cfg.AgentType),
		Description: "Deep research agent (" + string(cfg.AgentType) + ")",
		SupportedInterfaces: []*a2a.AgentInterface{
			a2a.NewAgentInterface(selfURL, a2a.TransportProtocolHTTPJSON),
		},
		Capabilities: a2a.AgentCapabilities{Streaming: true, PushNotifications: true, ExtendedAgentCard: true},
	}

	slog.SetLogLoggerLevel(slog.LevelInfo)

	handler := a2asrv.NewHandler(
		executor,
		domain.WithNodeInfo(domain.NodeInfo{Agent: cfg.AgentType}),
		a2asrv.WithClusterMode(a2asrv.ClusterConfig{
			TaskStore:    taskStore,
			QueueManager: eventQueueManager,
			WorkQueue:    workQueue,
			ContextCodec: &domain.ContextCodec{},
		}),
		a2asrv.WithPushNotifications(
			push.NewInMemoryStore(),
			msgstream.NewPushSender(msgstream.PushSenderConfig{Jetstream: js}),
		),
		a2asrv.WithExtendedAgentCard(card),
	)

	mux := http.NewServeMux()
	mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(card))
	mux.Handle("/reports/{id}", report.NewServer(taskStore))
	mux.Handle("/", a2asrv.NewRESTHandler(handler))

	srv := &http.Server{Handler: mux, ReadHeaderTimeout: 30 * time.Second}
	go func() {
		if err := srv.Serve(ln); err != nil {
			log.Error(ctx, "http server stopped", err)
		}
	}()
	log.Info(ctx, "server started", "node_type", cfg.AgentType, "url", selfURL, "listen", ln.Addr())

	return &Server{
		Addr: ln.Addr().String(),
		close: func() {
			cancelOutbox()
			_ = ln.Close()
			_ = db.Close()
			nc.Close()
		},
	}
}

func or(val, fallback string) string {
	if val != "" {
		return val
	}
	return fallback
}
