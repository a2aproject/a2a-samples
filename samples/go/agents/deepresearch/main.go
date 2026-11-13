package main

import (
	"context"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/server"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/utils"
	_ "github.com/go-sql-driver/mysql"
	"github.com/nats-io/nats.go"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/genai"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	srv := server.Start(ctx, configFromEnv())
	log.Info(ctx, "ready", "addr", srv.Addr)
	<-ctx.Done()
	srv.Close()
}

func configFromEnv() server.Config {
	envOr := func(key, fallback string) string {
		if v := os.Getenv(key); v != "" {
			return v
		}
		return fallback
	}
	nodeType := strings.ToLower(os.Getenv("NODE_TYPE"))
	if nodeType == "" {
		panic("NODE_TYPE environment variable is required")
	}
	apiKey := os.Getenv("GOOGLE_API_KEY")
	if apiKey == "" {
		panic("GOOGLE_API_KEY environment variable is required")
	}
	return server.Config{
		AgentType:      domain.AgentType(nodeType),
		ListenAddr:     envOr("LISTEN_ADDR", ":8080"),
		SelfURL:        envOr("SERVICE_URL", ""),
		ReportURL:      envOr("REPORT_URL", ""),
		NatsURL:        envOr("NATS_URL", nats.DefaultURL),
		MySQLDSN:       envOr("MYSQL_DSN", "root:root@tcp(localhost:3306)/planner?parseTime=true"),
		ResearcherURL:  envOr("RESEARCHER_URL", ""),
		AnalyzerURL:    envOr("ANALYZER_URL", ""),
		SynthesizerURL: envOr("SYNTHESIZER_URL", ""),
		Model:          utils.Must(gemini.NewModel(context.Background(), "gemini-3.1-flash-lite", &genai.ClientConfig{APIKey: apiKey})),
	}
}
