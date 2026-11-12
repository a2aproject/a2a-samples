package watch

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	reset = "\x1b[0m"
	bold  = "\x1b[1m"
	dim   = "\x1b[2m"
	red   = "\x1b[31m"
	green = "\x1b[32m"
)

// palette colors the servers in the order they first appear.
var palette = []string{"\x1b[34m", "\x1b[35m", "\x1b[36m", "\x1b[33m", "\x1b[32m", "\x1b[94m", "\x1b[95m", "\x1b[96m"}

// screen renders the model as lines of at most width visible characters.
type screen struct {
	m      *model
	now    time.Time
	width  int
	height int
	ttl    time.Duration
	title  string
	colors map[string]string
}

func (s *screen) color(server string) string {
	c, ok := s.colors[server]
	if !ok {
		c = palette[len(s.colors)%len(palette)]
		s.colors[server] = c
	}
	return c
}

func (s *screen) lines() []string {
	m := s.m
	var out []string
	add := func(format string, args ...any) { out = append(out, fmt.Sprintf(format, args...)) }

	servers := m.visibleServers(s.now)
	live := 0
	for _, srv := range servers {
		if srv.state(s.now) == "live" || srv.state(s.now) == "draining" {
			live++
		}
	}
	memory := green + "0 forgotten" + reset
	if m.failedChecks > 0 {
		memory = red + bold + fmt.Sprintf("%d forgotten", m.failedChecks) + reset
	}
	add("%s%s%s  ·  %d servers  ·  %d conversations  ·  %d turns  ·  %d memory checks, %s  ·  %d resent",
		bold, s.title, reset, live, len(m.conversations), m.turns, m.checks, memory, m.resent)
	add("")

	owned := map[string]int{}
	for n := range m.shards {
		if o, stale := m.owner(n); o != "" && !stale {
			owned[o]++
		}
	}
	conversations := map[string]int{}
	for _, c := range m.conversations {
		conversations[c.server]++
	}
	for _, srv := range servers {
		c := s.color(srv.name)
		state := srv.state(s.now)
		mark, stateColor := "●", green
		switch {
		case state == "gone":
			mark, stateColor = "✖", red
		case strings.HasPrefix(state, "silent"):
			mark, stateColor = "✖", red
			state = fmt.Sprintf("no heartbeat %ds/%ds", int(s.now.Sub(srv.seen).Seconds()), int(s.ttl.Seconds()))
		case state == "draining":
			mark, stateColor = "◐", "\x1b[33m"
		}
		add("  %s%-9s%s %s%s %-20s%s %3d shards  %2d agents  %2d conversations",
			c+bold, srv.name, reset, stateColor, mark, state, reset, owned[srv.name], len(srv.agents), conversations[srv.name])
	}
	add("")
	add("  shards  %s", s.strip())
	add("")

	convs := m.sortedConversations()
	const minLogRows = 5
	room := s.height - len(out) - minLogRows - 3
	add("  %s%-10s %-10s %5s  %-7s %s%s", dim, "USER", "SERVER", "TURNS", "MEMORY", "NOW", reset)
	for i, c := range convs {
		if i >= room && room >= 0 {
			add("  %s… %d more%s", dim, len(convs)-i, reset)
			break
		}
		add("  %s", s.conversationRow(c))
	}
	add("")
	logRows := max(minLogRows, s.height-len(out))
	start := max(0, len(m.log)-logRows)
	for _, l := range m.log[start:] {
		add("  %s%s%s %s", dim, l.at.Format("15:04:05"), reset, l)
	}
	for i := range out {
		out[i] = truncate(out[i], s.width)
	}
	return out
}

func (s *screen) strip() string {
	var sb strings.Builder
	for n := range s.m.shards {
		if n > 0 && n%8 == 0 {
			sb.WriteByte(' ')
		}
		o, stale := s.m.owner(n)
		switch {
		case o == "":
			sb.WriteString(dim + "░" + reset)
		case stale:
			sb.WriteString(red + "▒" + reset)
		default:
			sb.WriteString(s.color(o) + "█" + reset)
		}
	}
	return sb.String()
}

func (s *screen) conversationRow(c *conversation) string {
	server := c.server
	if server == "" {
		server = "?"
	}
	memory := ""
	switch {
	case c.failed > 0:
		memory = red + fmt.Sprintf("✗ %d/%d", c.failed, c.ok+c.failed) + reset
	case c.ok > 0:
		memory = green + fmt.Sprintf("✓ %d", c.ok) + reset
	}
	now := ""
	switch {
	case c.working != "":
		now = fmt.Sprintf("working: %q", c.working)
	case c.turns > 0:
		now = dim + "idle" + reset
	}
	if c.movedFrom != "" && s.now.Sub(c.movedAt) < movedFor {
		now = fmt.Sprintf("\x1b[33mmoved from %s (%s)%s %s", c.movedFrom, c.movedHow, reset, now)
	}
	return fmt.Sprintf("%-10s %s%-10s%s %5d  %s %s",
		c.name(), s.color(server), server, reset, c.turns, pad(memory, 7), now)
}

// pad pads a string with escapes to n visible characters.
func pad(text string, n int) string {
	if w := visible(text); w < n {
		return text + strings.Repeat(" ", n-w)
	}
	return text
}

func visible(text string) int {
	n, esc := 0, false
	for _, r := range text {
		switch {
		case esc:
			esc = r != 'm'
		case r == '\x1b':
			esc = true
		default:
			n++
		}
	}
	return n
}

// truncate cuts a string with escapes to width visible characters.
func truncate(text string, width int) string {
	if width <= 0 || visible(text) <= width {
		return text
	}
	var sb strings.Builder
	n, esc := 0, false
	for i, r := range text {
		switch {
		case esc:
			esc = r != 'm'
		case r == '\x1b':
			esc = true
		default:
			if n == width-1 {
				sb.WriteString("…" + reset)
				return sb.String()
			}
			n++
		}
		sb.WriteString(text[i : i+utf8.RuneLen(r)])
	}
	return sb.String()
}
