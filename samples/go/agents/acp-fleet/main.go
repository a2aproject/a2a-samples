package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/crowd"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/fakeacp"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/mcpscratch"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/server"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/status"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/watch"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
	"golang.org/x/term"
)

const usage = `usage: acp-fleet [serve | fakeacp | mcp <dir> | status | watch | crowd [users]]

  serve     run a fleet server, configured with environment variables (default)
  fakeacp   run the fake ACP agent on stdio
  mcp       run the scratch MCP server for <dir> on stdio
  status    print the servers of the fleet and the shards they own
  watch     show the servers, shards and conversations of the fleet live
  crowd     simulate users who talk to the fleet at FLEET_URL and check what their agents remember`

func main() {
	cmd := "serve"
	if len(os.Args) > 1 {
		cmd = os.Args[1]
	}
	var err error
	switch cmd {
	case "serve":
		err = serve()
	case "fakeacp":
		err = fakeacp.Run(fakeacp.Config{Server: os.Getenv("SERVER"), Home: os.Getenv("HOME")}, os.Stdin, os.Stdout)
	case "mcp":
		if len(os.Args) != 3 {
			err = fmt.Errorf("%s", usage)
			break
		}
		err = mcpscratch.Run(os.Args[2], os.Stdin, os.Stdout)
	case "status":
		err = printStatus()
	case "watch":
		err = runWatch()
	case "crowd":
		users := 6
		if len(os.Args) > 2 {
			users, err = strconv.Atoi(os.Args[2])
			if err != nil {
				break
			}
		}
		err = runCrowd(users)
	default:
		err = fmt.Errorf("%s", usage)
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "acp-fleet %s: %v\n", cmd, err)
		os.Exit(1)
	}
}

func serve() error {
	signals, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	name, err := os.Hostname()
	if err != nil {
		return err
	}
	cfg := server.Config{
		Name:           env("SERVER_NAME", name),
		ListenAddr:     env("LISTEN_ADDR", ":8080"),
		PublicURL:      env("PUBLIC_URL", "http://localhost:8080"),
		NATSURL:        env("NATS_URL", nats.DefaultURL),
		MySQLDSN:       env("MYSQL_DSN", "root:root@tcp(localhost:3306)/fleet?parseTime=true"),
		DataDir:        env("DATA_DIR", "/var/lib/acp-fleet"),
		AgentCommand:   strings.Fields(env("AGENT_COMMAND", exe+" fakeacp")),
		MCPCommand:     []string{exe, "mcp"},
		Shards:         envInt("SHARDS", 64),
		ScratchLimit:   int64(envInt("SCRATCH_LIMIT_MB", 64)) << 20,
		IdleTimeout:    envDuration("IDLE_TIMEOUT", time.Minute),
		DrainTimeout:   envDuration("DRAIN_TIMEOUT", time.Minute),
		MaxAgents:      envInt("MAX_AGENTS", 8),
		OutboxInterval: envDuration("OUTBOX_INTERVAL", 50*time.Millisecond),
		Heartbeat:      envDuration("HEARTBEAT", 2*time.Second),
		HeartbeatTTL:   envDuration("HEARTBEAT_TTL", 8*time.Second),
		OnLost: func() {
			fmt.Fprintln(os.Stderr, "acp-fleet: lost the fleet membership, exiting so that other servers can take over")
			os.Exit(1)
		},
	}
	srv, err := server.Start(context.Background(), cfg)
	if err != nil {
		return err
	}
	<-signals.Done()
	shutdownCtx, cancelShutdown := context.WithTimeout(context.Background(), cfg.DrainTimeout+30*time.Second)
	defer cancelShutdown()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Error(shutdownCtx, "shutdown failed", err)
		return err
	}
	return nil
}

func printStatus() error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	nc, err := nats.Connect(env("NATS_URL", nats.DefaultURL))
	if err != nil {
		return err
	}
	defer nc.Close()
	js, err := jetstream.New(nc)
	if err != nil {
		return err
	}
	return status.Print(ctx, js, os.Stdout)
}

func runWatch() error {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	nc, err := nats.Connect(env("NATS_URL", nats.DefaultURL), nats.MaxReconnects(-1))
	if err != nil {
		return err
	}
	defer nc.Close()
	return watch.Run(ctx, watch.Config{
		NATS:         nc,
		Shards:       envInt("SHARDS", 64),
		HeartbeatTTL: envDuration("HEARTBEAT_TTL", 8*time.Second),
		Title:        "acp-fleet " + env("FLEET_URL", "http://localhost:8080"),
		Size: func() (int, int) {
			w, h, err := term.GetSize(int(os.Stdout.Fd()))
			if err != nil {
				return 120, 40
			}
			return w, h
		},
	}, os.Stdout)
}

func runCrowd(users int) error {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	nc, err := nats.Connect(env("NATS_URL", nats.DefaultURL), nats.MaxReconnects(-1))
	if err != nil {
		return err
	}
	defer nc.Close()
	return crowd.Run(ctx, crowd.Config{
		URL:    env("FLEET_URL", "http://localhost:8080"),
		Users:  users,
		Think:  envDuration("THINK", 10*time.Second),
		Events: events.NewPublisher(nc, ""),
		Out:    os.Stdout,
	})
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	if v, err := strconv.Atoi(os.Getenv(key)); err == nil {
		return v
	}
	return fallback
}

func envDuration(key string, fallback time.Duration) time.Duration {
	if v, err := time.ParseDuration(os.Getenv(key)); err == nil {
		return v
	}
	return fallback
}
