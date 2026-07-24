package itest_test

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"testing"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/server"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/testutil"
)

func TestMain(m *testing.M) {
	cmd := exec.Command("docker", "compose", "--env-file", ".env", "-f", "infra/docker-compose.yaml", "up", "nats", "mysql", "-d")
	cmd.Dir = ".." // project root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "docker compose up failed: %v\n", err)
		os.Exit(1)
	}
	// Connectivity retries happen inside drtest.SetupNATS / drtest.SetupMySQL.
	os.Exit(m.Run())
}

// startAgent starts a single agent role on a random port and registers cleanup.
func startAgent(t *testing.T, agentType domain.AgentType, svcURLs map[domain.AgentType]string) *server.Server {
	t.Helper()
	srv := server.Start(context.Background(), server.Config{
		AgentType:      agentType,
		ListenAddr:     "127.0.0.1:0",
		NatsURL:        testutil.NatsURL,
		MySQLDSN:       testutil.MySQLDSN,
		Model:          &testutil.FakeLLM{},
		ResearcherURL:  svcURLs[domain.AgentResearcher],
		AnalyzerURL:    svcURLs[domain.AgentAnalyzer],
		SynthesizerURL: svcURLs[domain.AgentSynthesizer],
		OutboxInterval: 100 * time.Millisecond,
	})
	t.Cleanup(srv.Close)
	return srv
}

// waitForTerminal polls a task until it reaches a terminal state or the
// timeout expires.
func waitForTerminal(t *testing.T, client *a2aclient.Client, taskID a2a.TaskID, timeout time.Duration) *a2a.Task {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	for {
		task, err := client.GetTask(ctx, &a2a.GetTaskRequest{ID: taskID})
		if err != nil {
			t.Fatalf("GetTask(%s): %v", taskID, err)
		}
		if task.Status.State.Terminal() {
			return task
		}
		select {
		case <-ctx.Done():
			t.Fatalf("task %s still in state %s after %v", taskID, task.Status.State, timeout)
		case <-time.After(500 * time.Millisecond):
		}
	}
}

func TestFullPipeline(t *testing.T) {
	testutil.SetupNATS(t)
	testutil.SetupMySQL(t)

	// Start leaf agents, then orchestrator with their addresses.
	researcher := startAgent(t, domain.AgentResearcher, nil)
	analyzer := startAgent(t, domain.AgentAnalyzer, nil)
	synthesizer := startAgent(t, domain.AgentSynthesizer, nil)

	svcURLs := map[domain.AgentType]string{
		domain.AgentResearcher:  "http://" + researcher.Addr,
		domain.AgentAnalyzer:    "http://" + analyzer.Addr,
		domain.AgentSynthesizer: "http://" + synthesizer.Addr,
	}
	orch := startAgent(t, domain.AgentOrchestrator, svcURLs)

	// Client.
	ctx := context.Background()
	iface := a2a.NewAgentInterface("http://"+orch.Addr, a2a.TransportProtocolHTTPJSON)
	client, err := a2aclient.NewFromEndpoints(ctx, []*a2a.AgentInterface{iface})
	if err != nil {
		t.Fatalf("create client: %v", err)
	}

	// Send message.
	result, err := client.SendMessage(ctx, &a2a.SendMessageRequest{
		Message: a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("Research the impact of AI on healthcare")),
	})
	if err != nil {
		t.Fatalf("SendMessage: %v", err)
	}
	taskID := result.TaskInfo().TaskID
	t.Logf("task created: %s", taskID)

	// Wait for the full pipeline to complete.
	task := waitForTerminal(t, client, taskID, 30*time.Second)
	t.Logf("task finished in state %s", task.Status.State)

	if task.Status.State != a2a.TaskStateCompleted {
		t.Errorf("expected completed, got %s", task.Status.State)
	}
}
