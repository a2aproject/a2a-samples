// Package watch shows the fleet live in a terminal: the servers, which
// server owns each shard, the conversations and what happens to them.
package watch

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"strings"
	"time"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

const frame = 250 * time.Millisecond

// Config configures [Run].
type Config struct {
	NATS *nats.Conn
	// Shards is the number of shards of the fleet.
	Shards int
	// HeartbeatTTL is how long the servers wait for a silent server's heartbeat.
	HeartbeatTTL time.Duration
	// Title is the first thing on the header line.
	Title string
	// Size returns the terminal's width and height.
	Size func() (width, height int)
}

type update struct {
	bucket string
	key    string
	value  []byte
	event  *events.Event
}

// Run draws the fleet to w until ctx ends.
func Run(ctx context.Context, cfg Config, w io.Writer) error {
	js, err := jetstream.New(cfg.NATS)
	if err != nil {
		return err
	}
	updates := make(chan update, 1024)
	sub, err := cfg.NATS.Subscribe(events.Subject+".>", func(msg *nats.Msg) {
		var e events.Event
		if err := json.Unmarshal(msg.Data, &e); err != nil {
			return
		}
		select {
		case updates <- update{event: &e}:
		case <-ctx.Done():
		}
	})
	if err != nil {
		return err
	}
	defer func() {
		if err := sub.Unsubscribe(); err != nil && !errors.Is(err, nats.ErrConnectionClosed) {
			log.Warn(ctx, "unsubscribing from events failed", "cause", err)
		}
	}()
	for _, bucket := range []string{"NODES", "SHARDS"} {
		go watchBucket(ctx, js, bucket, updates)
	}

	m := newModel(cfg.Shards)
	s := &screen{m: m, ttl: cfg.HeartbeatTTL, title: cfg.Title, colors: map[string]string{}}
	if _, err := io.WriteString(w, "\x1b[?25l\x1b[2J"); err != nil {
		return err
	}
	ticker := time.NewTicker(frame)
	defer ticker.Stop()
	var last string
	for {
		select {
		case <-ctx.Done():
			_, err := io.WriteString(w, "\x1b[?25h\n")
			return err
		case u := <-updates:
			apply(m, u)
		case <-ticker.C:
			s.now = time.Now()
			s.width, s.height = cfg.Size()
			// Unchanged frames aren't drawn, so that recordings can skip idle time.
			next := strings.Join(s.lines(), "\n")
			if next == last {
				continue
			}
			last = next
			if err := draw(w, strings.Split(next, "\n"), s.height); err != nil {
				return err
			}
		}
	}
}

func apply(m *model, u update) {
	switch {
	case u.event != nil:
		m.event(*u.event)
	case u.bucket == "NODES":
		m.node(time.Now(), u.key, u.value)
	case u.bucket == "SHARDS" && u.value != nil:
		m.record(u.key, u.value)
	}
}

func draw(w io.Writer, lines []string, height int) error {
	if height > 0 && len(lines) > height {
		lines = lines[:height]
	}
	// No newline after the last line, so that a full screen doesn't scroll.
	_, err := io.WriteString(w, "\x1b[H"+strings.Join(lines, "\x1b[K\r\n")+"\x1b[K\x1b[J")
	return err
}

// watchBucket sends the updates of a KV bucket, waiting for the fleet to create it.
func watchBucket(ctx context.Context, js jetstream.JetStream, bucket string, updates chan<- update) {
	for ctx.Err() == nil {
		kv, err := js.KeyValue(ctx, bucket)
		if err != nil {
			sleep(ctx, time.Second)
			continue
		}
		watcher, err := kv.WatchAll(ctx)
		if err != nil {
			sleep(ctx, time.Second)
			continue
		}
		for e := range watcher.Updates() {
			if e == nil {
				continue
			}
			u := update{bucket: bucket, key: e.Key()}
			if e.Operation() == jetstream.KeyValuePut {
				u.value = e.Value()
			}
			select {
			case updates <- u:
			case <-ctx.Done():
			}
		}
		if err := watcher.Stop(); err != nil && ctx.Err() == nil {
			sleep(ctx, time.Second)
		}
	}
}

func sleep(ctx context.Context, d time.Duration) {
	select {
	case <-ctx.Done():
	case <-time.After(d):
	}
}
