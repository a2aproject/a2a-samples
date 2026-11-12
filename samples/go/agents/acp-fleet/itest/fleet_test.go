package itest_test

import (
	"context"
	"errors"
	"fmt"
	"net"
	"os"
	"os/exec"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/fakeacp"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/mcpscratch"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/server"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/mysql/mysqltest"
	"github.com/a2aproject/a2a-samples/samples/go/integrations/nats/natstest"
	"github.com/nats-io/nats.go/jetstream"
)

const shardCount = 8

// TestMain runs the fake agent and the MCP server when the servers under test
// start the test binary as their agent.
func TestMain(m *testing.M) {
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "fakeacp":
			exit(fakeacp.Run(fakeacp.Config{Server: os.Getenv("SERVER"), Home: os.Getenv("HOME")}, os.Stdin, os.Stdout))
		case "mcp":
			exit(mcpscratch.Run(os.Args[2], os.Stdin, os.Stdout))
		}
	}
	if err := os.Setenv("GORACE", "atexit_sleep_ms=0"); err != nil {
		exit(err)
	}
	if !listening("localhost:4222") || !listening("localhost:3306") {
		cmd := exec.Command("docker", "compose", "-f", "compose.yaml", "up", "-d")
		cmd.Dir = "../../../integrations/mysql"
		cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
		if err := cmd.Run(); err != nil {
			exit(fmt.Errorf("docker compose up: %w", err))
		}
	}
	os.Exit(m.Run())
}

func exit(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	os.Exit(0)
}

func listening(addr string) bool {
	conn, err := net.DialTimeout("tcp", addr, time.Second)
	if err != nil {
		return false
	}
	return conn.Close() == nil
}

type fleet struct {
	t       *testing.T
	mu      sync.Mutex
	servers map[string]*server.Server
}

func newFleet(t *testing.T, names ...string) *fleet {
	t.Helper()
	return newFleetWith(t, 0, names...)
}

func newFleetWith(t *testing.T, scratchLimit int64, names ...string) *fleet {
	t.Helper()
	_, js := natstest.Connect(t)
	ctx := context.Background()
	for _, bucket := range []string{"NODES", "SHARDS", "OUTBOX"} {
		natstest.ResetKeyValue(t, js, bucket)
	}
	if err := js.DeleteObjectStore(ctx, "SHARD_DATA"); err != nil && !errors.Is(err, jetstream.ErrStreamNotFound) {
		t.Fatalf("js.DeleteObjectStore() error = %v", err)
	}
	natstest.ResetStreams(t, js, natstest.EventsStream)
	mysqltest.Open(t)

	f := &fleet{t: t, servers: map[string]*server.Server{}}
	for _, name := range names {
		f.startWith(name, scratchLimit)
	}
	f.waitOwned(names...)
	return f
}

func (f *fleet) start(name string) {
	f.t.Helper()
	f.startWith(name, 0)
}

func (f *fleet) startWith(name string, scratchLimit int64) {
	f.t.Helper()
	dataDir := f.t.TempDir()
	srv, err := server.Start(context.Background(), server.Config{
		Name:           name,
		ListenAddr:     "127.0.0.1:0",
		PublicURL:      "http://localhost",
		NATSURL:        natstest.URL,
		MySQLDSN:       mysqltest.DSN,
		DataDir:        dataDir,
		AgentCommand:   []string{os.Args[0], "fakeacp"},
		MCPCommand:     []string{os.Args[0], "mcp"},
		Shards:         shardCount,
		ScratchLimit:   scratchLimit,
		IdleTimeout:    time.Minute,
		DrainTimeout:   10 * time.Second,
		MaxAgents:      8,
		OutboxInterval: 20 * time.Millisecond,
		Heartbeat:      300 * time.Millisecond,
		HeartbeatTTL:   2 * time.Second,
		OnLost:         func() { f.t.Errorf("%s lost its membership", name) },
	})
	if err != nil {
		f.t.Fatalf("server.Start(%s) error = %v", name, err)
	}
	f.mu.Lock()
	f.servers[name] = srv
	f.mu.Unlock()
	f.t.Cleanup(func() {
		if s := f.remove(name); s != nil {
			if err := s.Kill(); err != nil {
				f.t.Logf("Kill(%s) error = %v", name, err)
			}
		}
	})
}

func (f *fleet) remove(name string) *server.Server {
	f.mu.Lock()
	defer f.mu.Unlock()
	s := f.servers[name]
	delete(f.servers, name)
	return s
}

// waitOwned waits until every shard is owned by the server rendezvous hashing assigns it to among names.
func (f *fleet) waitOwned(names ...string) {
	f.t.Helper()
	_, js := natstest.Connect(f.t)
	ctx := context.Background()
	deadline := time.Now().Add(20 * time.Second)
	for {
		kv, err := js.KeyValue(ctx, "SHARDS")
		done := err == nil
		for s := 0; done && s < shardCount; s++ {
			e, err := kv.Get(ctx, fmt.Sprintf("s%03d", s))
			done = err == nil && strings.Contains(string(e.Value()), `"owner":"`+shards.Assign(s, names)+`"`)
		}
		if done {
			return
		}
		if time.Now().After(deadline) {
			f.t.Fatalf("shards not owned by %v after 20s", names)
		}
		time.Sleep(100 * time.Millisecond)
	}
}

func (f *fleet) client(name string) *a2aclient.Client {
	f.t.Helper()
	f.mu.Lock()
	addr := f.servers[name].Addr
	f.mu.Unlock()
	c, err := a2aclient.NewFromEndpoints(context.Background(), []*a2a.AgentInterface{a2a.NewAgentInterface("http://"+addr, a2a.TransportProtocolHTTPJSON)})
	if err != nil {
		f.t.Fatalf("a2aclient.NewFromEndpoints() error = %v", err)
	}
	f.t.Cleanup(func() {
		if err := c.Destroy(); err != nil {
			f.t.Logf("Destroy() error = %v", err)
		}
	})
	return c
}

// send sends text through the server and returns the resulting task.
func (f *fleet) send(via, contextID string, taskID a2a.TaskID, text string) *a2a.Task {
	f.t.Helper()
	msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(text))
	msg.ContextID, msg.TaskID = contextID, taskID
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	res, err := f.client(via).SendMessage(ctx, &a2a.SendMessageRequest{Message: msg})
	if err != nil {
		f.t.Fatalf("SendMessage(%q via %s) error = %v", text, via, err)
	}
	task, ok := res.(*a2a.Task)
	if !ok {
		f.t.Fatalf("SendMessage(%q via %s) = %T, want *a2a.Task", text, via, res)
	}
	return task
}

func reply(task *a2a.Task) string {
	var sb strings.Builder
	for _, art := range task.Artifacts {
		for _, p := range art.Parts {
			sb.WriteString(p.Text())
		}
	}
	return sb.String()
}

// conversationOn returns a new context ID whose shard rendezvous hashing assigns to owner among names.
func conversationOn(owner string, names ...string) string {
	for {
		id := a2a.NewContextID()
		if shards.Assign(shards.Of(id, shardCount), names) == owner {
			return id
		}
	}
}

func wantReply(t *testing.T, task *a2a.Task, want ...string) {
	t.Helper()
	got := reply(task)
	for _, w := range want {
		if !strings.Contains(got, w) {
			t.Fatalf("reply = %q, want it to contain %q", got, w)
		}
	}
}

func TestFleet_routesEveryMessageToTheShardOwner(t *testing.T) {
	names := []string{"server-1", "server-2", "server-3"}
	f := newFleet(t, names...)
	c := conversationOn("server-2", names...)

	wantReply(t, f.send("server-1", c, "", "hi"), "server-2: turn 1, new session", "MCP: scratch")
	wantReply(t, f.send("server-3", c, "", "again"), "server-2: turn 2, same process")
	asked := f.send("server-1", c, "", "save milk")
	if asked.Status.State != a2a.TaskStateInputRequired {
		t.Fatalf("save state = %v, want input-required", asked.Status.State)
	}
	answered := f.send("server-3", c, asked.ID, "once")
	if answered.Status.State != a2a.TaskStateCompleted {
		t.Fatalf("answer state = %v, want completed", answered.Status.State)
	}
	wantReply(t, answered, "server-2: turn 3, saved. Notes: milk")
}

func TestFleet_crashedOwnersShardMovesWithItsHomeAndScratch(t *testing.T) {
	names := []string{"server-1", "server-2", "server-3"}
	f := newFleet(t, names...)
	c := conversationOn("server-2", names...)
	f.send("server-1", c, "", "hi")
	asked := f.send("server-1", c, "", "save milk")
	f.send("server-3", c, asked.ID, "once")
	f.send("server-1", c, "", "scratch draft")

	working := make(chan *a2a.Task, 1)
	go func() { working <- f.sendAsync("server-1", c, "work 30") }()
	time.Sleep(2 * time.Second)
	if err := f.remove("server-2").Kill(); err != nil {
		t.Fatalf("Kill() error = %v", err)
	}

	if task := <-working; task == nil || task.Status.State != a2a.TaskStateFailed {
		t.Fatalf("interrupted task = %+v, want failed", task)
	}
	survivors := []string{"server-1", "server-3"}
	f.waitOwned(survivors...)
	owner := shards.Assign(shards.Of(c, shardCount), survivors)
	wantReply(t, f.send("server-1", c, "", "remember?"),
		owner+": turn 4, session loaded; turns 1-3 ran on server-2", "Notes: milk.")
	wantReply(t, f.send("server-3", c, "", "scratch after"), owner+": turn 5, scratch.txt: draft, after")
}

func TestFleet_crashLosesScratchOverTheLimit(t *testing.T) {
	names := []string{"server-1", "server-2", "server-3"}
	f := newFleetWith(t, 1, names...)
	c := conversationOn("server-2", names...)
	f.send("server-1", c, "", "scratch draft")

	if err := f.remove("server-2").Kill(); err != nil {
		t.Fatalf("Kill() error = %v", err)
	}
	survivors := []string{"server-1", "server-3"}
	f.waitOwned(survivors...)
	owner := shards.Assign(shards.Of(c, shardCount), survivors)
	wantReply(t, f.send("server-1", c, "", "remember?"), owner+": turn 2, session loaded", "Scratch was lost")
}

func TestFleet_drainFinishesTurnsAndMovesScratch(t *testing.T) {
	names := []string{"server-1", "server-2", "server-3"}
	f := newFleet(t, names...)
	c := conversationOn("server-2", names...)
	f.send("server-1", c, "", "scratch keep-me")

	working := make(chan *a2a.Task, 1)
	go func() { working <- f.sendAsync("server-1", c, "work 3") }()
	time.Sleep(time.Second)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := f.remove("server-2").Shutdown(ctx); err != nil {
		t.Fatalf("Shutdown() error = %v", err)
	}
	if task := <-working; task == nil || task.Status.State != a2a.TaskStateCompleted {
		t.Fatalf("task running during the drain = %+v, want completed", task)
	}
	survivors := []string{"server-1", "server-3"}
	owner := shards.Assign(shards.Of(c, shardCount), survivors)
	wantReply(t, f.send("server-3", c, "", "scratch after"), owner+": turn 3, scratch.txt: keep-me, after")
}

func TestFleet_joiningServerTakesItsShards(t *testing.T) {
	f := newFleet(t, "server-1", "server-2")
	all := []string{"server-1", "server-2", "server-3"}
	c := conversationOn("server-3", all...)
	f.send("server-1", c, "", "scratch before")

	f.start("server-3")
	f.waitOwned(all...)
	wantReply(t, f.send("server-1", c, "", "scratch after"), "server-3: turn 2, scratch.txt: before, after")
}

func (f *fleet) sendAsync(via, contextID, text string) *a2a.Task {
	msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(text))
	msg.ContextID = contextID
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	res, err := f.client(via).SendMessage(ctx, &a2a.SendMessageRequest{Message: msg})
	if err != nil {
		f.t.Errorf("SendMessage(%q) error = %v", text, err)
		return nil
	}
	task, _ := res.(*a2a.Task)
	return task
}
