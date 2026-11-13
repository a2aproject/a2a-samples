package watch

import (
	"encoding/json"
	"fmt"
	"slices"
	"sort"
	"strings"
	"time"

	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/nodes"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
)

const (
	// silentAfter marks a server silent when its record wasn't rewritten for this long.
	silentAfter = 3 * time.Second
	// goneFor keeps a server that left on screen for this long.
	goneFor = 45 * time.Second
	// movedFor keeps the mark of a conversation that moved for this long.
	movedFor = 20 * time.Second
	maxLog   = 50
	// mergeWithin merges claims of the same kind into one log line.
	mergeWithin = 3 * time.Second
)

type server struct {
	name     string
	draining bool
	seen     time.Time
	left     time.Time
	agents   map[string]bool
}

type conversation struct {
	id      string
	user    string
	first   time.Time
	server  string
	shard   int
	turns   int
	working string
	ok      int
	failed  int
	resent  int
	// uploaded and size describe the snapshot saved after the last turn.
	uploaded int64
	size     int64
	// movedFrom is the server the conversation's shard was taken from.
	movedFrom string
	movedAt   time.Time
	// movedHow is crashed, drained or rebalanced.
	movedHow string
	// confirmed is set once a check passed after the move.
	confirmed bool
}

type logLine struct {
	at    time.Time
	text  string
	key   string
	count int
	convs int
}

// model is what the watch view shows, built from the fleet's KV buckets and events.
type model struct {
	shards        int
	servers       map[string]*server
	records       map[int]shards.Record
	conversations map[string]*conversation
	// releasedBy is the server that released a free shard: a graceful
	// release frees the record, so the claim that follows has no previous owner.
	releasedBy   map[int]string
	log          []*logLine
	turns        int
	checks       int
	failedChecks int
	resent       int
	// uploaded and saved total the snapshots saved after turns.
	uploaded int64
	saved    int64
}

func newModel(count int) *model {
	return &model{
		shards:        count,
		servers:       map[string]*server{},
		records:       map[int]shards.Record{},
		conversations: map[string]*conversation{},
		releasedBy:    map[int]string{},
	}
}

func (m *model) server(name string) *server {
	s, ok := m.servers[name]
	if !ok {
		s = &server{name: name, agents: map[string]bool{}}
		m.servers[name] = s
	}
	return s
}

// node applies a write of a server's record, or its deletion when data is nil.
func (m *model) node(now time.Time, key string, data []byte) {
	if data == nil {
		s, ok := m.servers[key]
		if !ok || !s.left.IsZero() {
			return
		}
		s.left = now
		clear(s.agents)
		m.addLog(now, key+" left the fleet", "", 0)
		return
	}
	var n nodes.Node
	if err := json.Unmarshal(data, &n); err != nil {
		return
	}
	s, known := m.servers[n.Name]
	if !known || !s.left.IsZero() {
		s = m.server(n.Name)
		s.left = time.Time{}
		m.addLog(now, n.Name+" joined the fleet", "", 0)
	}
	if n.Draining && !s.draining {
		m.addLog(now, n.Name+" is draining: its turns finish, then its shards move", "", 0)
	}
	s.draining = n.Draining
	s.seen = now
}

// record applies a write of a shard's record.
func (m *model) record(key string, data []byte) {
	var n int
	if _, err := fmt.Sscanf(key, "s%d", &n); err != nil {
		return
	}
	var r shards.Record
	if err := json.Unmarshal(data, &r); err != nil {
		return
	}
	m.records[n] = r
}

func (m *model) conversation(e events.Event) *conversation {
	if e.Context == "" {
		return nil
	}
	c, ok := m.conversations[e.Context]
	if !ok {
		c = &conversation{id: e.Context, first: e.Time, shard: e.Shard}
		m.conversations[e.Context] = c
	}
	if e.User != "" {
		c.user = e.User
	}
	return c
}

func (m *model) event(e events.Event) {
	now := e.Time
	switch e.Kind {
	case events.Routed:
		c := m.conversation(e)
		c.server = e.Owner
		path := "lb → " + e.Server
		if e.Owner != e.Server {
			path += " → " + e.Owner
		}
		m.addLog(now, fmt.Sprintf("%-8s %-30s %q", c.name(), path, e.Text), "", 0)
	case events.AgentStarted:
		m.conversation(e).server = e.Server
		m.server(e.Server).agents[e.Context] = true
	case events.AgentStopped:
		delete(m.server(e.Server).agents, e.Context)
	case events.TurnStarted:
		c := m.conversation(e)
		c.server, c.working = e.Server, e.Text
	case events.TurnEnded:
		c := m.conversation(e)
		c.working = ""
		c.turns++
		m.turns++
		c.uploaded, c.size = e.Uploaded, e.Size
		m.uploaded += e.Uploaded
		m.saved += e.Size
	case events.TaskFailed:
		c := m.conversation(e)
		c.working = ""
		c.resent++
		m.resent++
		m.addLog(now, fmt.Sprintf("%s's turn stopped with %s; the message is sent again", c.name(), c.movedFromOr("its server")), "", 0)
	case events.Released:
		m.releasedBy[e.Shard] = e.Server
	case events.Claimed:
		m.claimed(e)
	case events.Checked:
		c := m.conversation(e)
		m.checks++
		if !e.OK {
			c.failed++
			m.failedChecks++
			m.addLog(now, fmt.Sprintf("✗ %s's agent forgot the %s", c.name(), e.Check), "", 0)
			return
		}
		c.ok++
		if c.movedFrom != "" && !c.confirmed {
			m.addLog(now, fmt.Sprintf("✓ %s's agent remembers the %s on %s after moving from %s", c.name(), e.Check, c.server, c.movedFrom), "", 0)
			c.confirmed = true
		}
	}
}

func (m *model) claimed(e events.Event) {
	if e.From == "" {
		e.From = m.releasedBy[e.Shard]
	}
	delete(m.releasedBy, e.Shard)
	if e.From == "" || e.From == e.Server {
		m.addLog(e.Time, e.Server+" claimed %d new shards", "new:"+e.Server, 0)
		return
	}
	var moved int
	for _, c := range m.conversations {
		if c.shard == e.Shard {
			moved++
		}
	}
	how := "drained"
	if e.Orphaned {
		how = "crashed"
	} else if s, ok := m.servers[e.From]; ok && !s.draining {
		how = "rebalanced"
	}
	for _, c := range m.conversations {
		if c.shard == e.Shard {
			c.movedFrom, c.movedAt, c.movedHow, c.confirmed = e.From, e.Time, how, false
			c.server, c.working = e.Server, ""
		}
	}
	m.addLog(e.Time, fmt.Sprintf("%s took %%d shards from %s (%s), %%d conversations", e.Server, e.From, how), "from:"+e.Server+e.From+how, moved)
}

// addLog appends a line. Lines with a key merge with the last line of the
// same key: their text is a format with the count and the conversations.
func (m *model) addLog(now time.Time, text, key string, convs int) {
	if key != "" {
		for i := len(m.log) - 1; i >= 0 && i >= len(m.log)-5; i-- {
			l := m.log[i]
			if l.key == key && now.Sub(l.at) < mergeWithin {
				l.count++
				l.convs += convs
				l.at = now
				return
			}
		}
	}
	m.log = append(m.log, &logLine{at: now, text: text, key: key, count: 1, convs: convs})
	if len(m.log) > maxLog {
		m.log = slices.Delete(m.log, 0, len(m.log)-maxLog)
	}
}

func (l *logLine) String() string {
	if l.key == "" {
		return l.text
	}
	if strings.Count(l.text, "%d") == 2 {
		return fmt.Sprintf(l.text, l.count, l.convs)
	}
	return fmt.Sprintf(l.text, l.count)
}

func (c *conversation) name() string {
	if c.user != "" {
		return c.user
	}
	return "you"
}

func (c *conversation) movedFromOr(fallback string) string {
	if c.movedFrom != "" {
		return c.movedFrom
	}
	return fallback
}

// state returns how the server looks now.
func (s *server) state(now time.Time) string {
	switch {
	case !s.left.IsZero():
		return "gone"
	case now.Sub(s.seen) > silentAfter:
		return fmt.Sprintf("silent %ds", int(now.Sub(s.seen).Seconds()))
	case s.draining:
		return "draining"
	}
	return "live"
}

// visibleServers returns the servers to show, sorted by name.
func (m *model) visibleServers(now time.Time) []*server {
	var out []*server
	for _, s := range m.servers {
		if !s.left.IsZero() && now.Sub(s.left) > goneFor {
			continue
		}
		out = append(out, s)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].name < out[j].name })
	return out
}

// owner returns the live owner of a shard, or "" if it is free or its owner stopped.
func (m *model) owner(n int) (name string, stale bool) {
	r := m.records[n]
	if r.Owner == "" {
		return "", false
	}
	s, ok := m.servers[r.Owner]
	return r.Owner, !ok || !s.left.IsZero()
}

func (m *model) sortedConversations() []*conversation {
	out := make([]*conversation, 0, len(m.conversations))
	for _, c := range m.conversations {
		out = append(out, c)
	}
	sort.Slice(out, func(i, j int) bool {
		if (out[i].user == "") != (out[j].user == "") {
			return out[i].user == ""
		}
		if out[i].user != out[j].user {
			return out[i].user < out[j].user
		}
		return out[i].first.Before(out[j].first)
	})
	return out
}
