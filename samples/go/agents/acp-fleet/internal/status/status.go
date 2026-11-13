// Package status prints which server owns which shards and conversations.
package status

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sort"
	"text/tabwriter"

	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/nodes"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
	"github.com/nats-io/nats.go/jetstream"
)

type server struct {
	node          nodes.Node
	shards        int
	conversations int
}

// Print writes the servers of the fleet and the shards they own to w.
func Print(ctx context.Context, js jetstream.JetStream, w io.Writer) error {
	servers := map[string]*server{}
	nodesKV, err := js.KeyValue(ctx, "NODES")
	if err != nil {
		return err
	}
	if err := each(ctx, nodesKV, func(_ string, data []byte) error {
		var n nodes.Node
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		servers[n.Name] = &server{node: n}
		return nil
	}); err != nil {
		return err
	}

	shardsKV, err := js.KeyValue(ctx, "SHARDS")
	if err != nil {
		return err
	}
	var free, orphaned []string
	if err := each(ctx, shardsKV, func(key string, data []byte) error {
		var r shards.Record
		if err := json.Unmarshal(data, &r); err != nil {
			return err
		}
		s, live := servers[r.Owner]
		switch {
		case r.Owner == "":
			free = append(free, key)
		case !live || s.node.Incarnation != r.Incarnation:
			orphaned = append(orphaned, key)
		default:
			s.shards++
			s.conversations += len(r.Homes)
		}
		return nil
	}); err != nil {
		return err
	}

	names := make([]string, 0, len(servers))
	for name := range servers {
		names = append(names, name)
	}
	sort.Strings(names)
	tw := tabwriter.NewWriter(w, 0, 4, 2, ' ', 0)
	if _, err := fmt.Fprintln(tw, "SERVER\tINCARNATION\tSTATE\tSHARDS\tCONVERSATIONS"); err != nil {
		return err
	}
	for _, name := range names {
		s := servers[name]
		state := "live"
		if s.node.Draining {
			state = "draining"
		}
		if _, err := fmt.Fprintf(tw, "%s\t%s\t%s\t%d\t%d\n", name, s.node.Incarnation, state, s.shards, s.conversations); err != nil {
			return err
		}
	}
	if err := tw.Flush(); err != nil {
		return err
	}
	if len(free) > 0 || len(orphaned) > 0 {
		_, err = fmt.Fprintf(w, "\nmoving: %d free, %d owned by a server that stopped\n", len(free), len(orphaned))
	}
	return err
}

func each(ctx context.Context, kv jetstream.KeyValue, fn func(key string, value []byte) error) error {
	keys, err := kv.Keys(ctx)
	if errors.Is(err, jetstream.ErrNoKeysFound) {
		return nil
	}
	if err != nil {
		return err
	}
	for _, k := range keys {
		e, err := kv.Get(ctx, k)
		if errors.Is(err, jetstream.ErrKeyNotFound) {
			continue
		}
		if err != nil {
			return err
		}
		if err := fn(k, e.Value()); err != nil {
			return err
		}
	}
	return nil
}
