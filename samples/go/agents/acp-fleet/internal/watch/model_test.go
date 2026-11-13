package watch

import (
	"regexp"
	"strings"
	"testing"
	"time"

	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/google/go-cmp/cmp"
)

var escapes = regexp.MustCompile("\x1b\\[[0-9;?]*[a-zA-Z]")

func render(m *model, now time.Time) string {
	s := &screen{m: m, now: now, width: 200, height: 60, ttl: 8 * time.Second, title: "fleet", colors: map[string]string{}}
	return escapes.ReplaceAllString(strings.Join(s.lines(), "\n"), "")
}

func TestModel_crashMovesConversationsAndCountsChecks(t *testing.T) {
	t.Parallel()
	start := time.Date(2026, 11, 12, 15, 0, 0, 0, time.UTC)
	at := func(s int) time.Time { return start.Add(time.Duration(s) * time.Second) }
	m := newModel(4)
	m.node(at(0), "server-1", []byte(`{"name":"server-1","incarnation":"a"}`))
	m.node(at(0), "server-2", []byte(`{"name":"server-2","incarnation":"b"}`))
	m.record("s000", []byte(`{"owner":"server-1","incarnation":"a"}`))
	m.record("s001", []byte(`{"owner":"server-2","incarnation":"b"}`))
	m.event(events.Event{Time: at(1), Kind: events.Routed, Server: "server-1", Owner: "server-2", Shard: 1, Context: "c1", User: "alice", Text: "hi"})
	m.event(events.Event{Time: at(1), Kind: events.TurnStarted, Server: "server-2", Shard: 1, Context: "c1", Text: "hi"})
	m.event(events.Event{Time: at(2), Kind: events.TurnEnded, Server: "server-2", Shard: 1, Context: "c1"})

	m.node(at(5), "server-2", nil)
	m.record("s001", []byte(`{"owner":"server-1","incarnation":"a"}`))
	m.event(events.Event{Time: at(5), Kind: events.Claimed, Server: "server-1", Shard: 1, From: "server-2", Orphaned: true})
	m.event(events.Event{Time: at(6), Kind: events.Checked, Context: "c1", User: "alice", Check: "code", OK: true})
	m.event(events.Event{Time: at(7), Kind: events.Checked, Context: "c1", User: "alice", Check: "file", OK: false})

	got := render(m, at(8))
	for _, want := range []string{
		"1 conversations",
		"1 turns",
		"2 memory checks, 1 forgotten",
		"server-2  ✖ gone",
		"alice      server-1",
		"moved from server-2 (crashed)",
		"server-1 took 1 shards from server-2 (crashed), 1 conversations",
		"✓ alice's agent remembers the code on server-1 after moving from server-2",
		"✗ alice's agent forgot the file",
		"alice    lb → server-1 → server-2",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("render() = \n%s\nwant it to contain %q", got, want)
		}
	}
}

func TestModel_gracefulMovesNameTheReleasingServer(t *testing.T) {
	t.Parallel()
	start := time.Date(2026, 11, 12, 15, 0, 0, 0, time.UTC)
	at := func(s int) time.Time { return start.Add(time.Duration(s) * time.Second) }
	m := newModel(4)
	m.node(at(0), "server-1", []byte(`{"name":"server-1","incarnation":"a"}`))
	m.node(at(0), "server-2", []byte(`{"name":"server-2","incarnation":"b"}`))
	m.event(events.Event{Time: at(1), Kind: events.Routed, Server: "server-1", Owner: "server-2", Shard: 1, Context: "c1", User: "bob"})
	m.node(at(2), "server-2", []byte(`{"name":"server-2","incarnation":"b","draining":true}`))
	m.event(events.Event{Time: at(3), Kind: events.Released, Server: "server-2", Shard: 1})
	m.event(events.Event{Time: at(3), Kind: events.Claimed, Server: "server-1", Shard: 1})
	m.event(events.Event{Time: at(4), Kind: events.Released, Server: "server-1", Shard: 2})
	m.event(events.Event{Time: at(4), Kind: events.Claimed, Server: "server-2", Shard: 2})

	got := render(m, at(5))
	for _, want := range []string{
		"server-1 took 1 shards from server-2 (drained), 1 conversations",
		"server-2 took 1 shards from server-1 (rebalanced), 0 conversations",
		"bob        server-1",
		"moved from server-2 (drained)",
		"server-2 took 1 shards from server-1 (rebalanced)",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("render() = \n%s\nwant it to contain %q", got, want)
		}
	}
}

func TestModel_mergesClaimsOfOneMove(t *testing.T) {
	t.Parallel()
	start := time.Date(2026, 11, 12, 15, 0, 0, 0, time.UTC)
	m := newModel(8)
	m.node(start, "server-3", []byte(`{"name":"server-3","incarnation":"c"}`))
	for i := range 3 {
		m.event(events.Event{Time: start.Add(time.Duration(i) * 100 * time.Millisecond), Kind: events.Claimed, Server: "server-3", Shard: i})
	}
	var got []string
	for _, l := range m.log {
		got = append(got, l.String())
	}
	want := []string{"server-3 joined the fleet", "server-3 claimed 3 new shards"}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Fatalf("model.log wrong result (-want +got) diff = %s", diff)
	}
}

func TestTruncate_keepsEscapesAndCutsVisibleText(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		text  string
		width int
		want  string
	}{
		{name: "short", text: "\x1b[1mabc\x1b[0m", width: 5, want: "\x1b[1mabc\x1b[0m"},
		{name: "cut", text: "\x1b[1mabcdef\x1b[0m", width: 4, want: "\x1b[1mabc…" + reset},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := truncate(tc.text, tc.width); got != tc.want {
				t.Fatalf("truncate(%q, %d) = %q, want %q", tc.text, tc.width, got, tc.want)
			}
		})
	}
}
