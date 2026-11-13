package shards

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"maps"
	"sync"
	"time"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/nats-io/nats.go/jetstream"
)

const (
	recordBucket = "SHARDS"
	objectBucket = "SHARD_DATA"
	// retention removes the snapshots of conversations nobody used for this
	// long, when their shard is claimed. Records are bounded by the shard
	// count and kept.
	retention = 7 * 24 * time.Hour
	// listingAge is how long the claims of a reconcile pass share one listing
	// of the object store.
	listingAge = 10 * time.Second
)

// Object is a snapshot in the object store.
type Object struct {
	Name  string    `json:"name"`
	Size  int64     `json:"size"`
	Saved time.Time `json:"saved"`
}

// Record is the state of a shard in the SHARDS bucket. A free shard has no owner.
type Record struct {
	Owner       string `json:"owner,omitempty"`
	Incarnation string `json:"incarnation,omitempty"`
	// Epoch grows with every claim.
	Epoch uint64 `json:"epoch"`
	// Sessions is the snapshot of the SQLite session map.
	Sessions Object `json:"sessions,omitzero"`
	// Homes are the snapshots of the agent homes by context ID, saved after every turn.
	Homes map[string]Object `json:"homes,omitempty"`
	// Scratch are the snapshots of scratch directories by context ID, saved
	// after every turn while they are within the scratch limit, and when the
	// shard moves gracefully.
	Scratch map[string]Object `json:"scratch,omitempty"`
}

func (r Record) clone() Record {
	r.Homes = maps.Clone(r.Homes)
	r.Scratch = maps.Clone(r.Scratch)
	return r
}

func key(shard int) string { return fmt.Sprintf("s%03d", shard) }

// Table is a cached view of all shard records, for routing.
type Table struct {
	kv  jetstream.KeyValue
	obj jetstream.ObjectStore

	mu      sync.Mutex
	records map[string]Record
	subs    []chan struct{}

	listMu   sync.Mutex
	listed   []string
	listedAt time.Time
}

// OpenTable creates the SHARDS bucket and the SHARD_DATA object store if
// needed, and keeps a view of the records until ctx ends.
func OpenTable(ctx context.Context, js jetstream.JetStream) (*Table, error) {
	kv, err := js.CreateOrUpdateKeyValue(ctx, jetstream.KeyValueConfig{Bucket: recordBucket})
	if err != nil {
		return nil, fmt.Errorf("creating the %s bucket: %w", recordBucket, err)
	}
	// No TTL: an unchanged chunk stays in use for as long as its conversation.
	obj, err := js.CreateOrUpdateObjectStore(ctx, jetstream.ObjectStoreConfig{Bucket: objectBucket})
	if err != nil {
		return nil, fmt.Errorf("creating the %s object store: %w", objectBucket, err)
	}
	t := &Table{kv: kv, obj: obj, records: map[string]Record{}}
	w, err := kv.WatchAll(ctx)
	if err != nil {
		return nil, fmt.Errorf("watching the %s bucket: %w", recordBucket, err)
	}
	ready := make(chan struct{})
	go t.watch(ctx, w, ready)
	select {
	case <-ready:
	case <-ctx.Done():
		return nil, ctx.Err()
	}
	return t, nil
}

// Get returns the cached record of the shard.
func (t *Table) Get(shard int) Record {
	t.mu.Lock()
	defer t.mu.Unlock()
	return t.records[key(shard)]
}

// All returns the cached records by shard key.
func (t *Table) All() map[string]Record {
	t.mu.Lock()
	defer t.mu.Unlock()
	return maps.Clone(t.records)
}

// Subscribe returns a channel that receives a value after a record changes.
func (t *Table) Subscribe() <-chan struct{} {
	ch := make(chan struct{}, 1)
	t.mu.Lock()
	t.subs = append(t.subs, ch)
	t.mu.Unlock()
	return ch
}

// objects returns the names in the object store. The listing can be up to
// listingAge old; objects uploaded since are missing from it.
func (t *Table) objects(ctx context.Context) ([]string, error) {
	t.listMu.Lock()
	defer t.listMu.Unlock()
	if time.Since(t.listedAt) < listingAge {
		return t.listed, nil
	}
	infos, err := t.obj.List(ctx)
	if err != nil && !errors.Is(err, jetstream.ErrNoObjectsFound) {
		return nil, fmt.Errorf("listing %s: %w", objectBucket, err)
	}
	names := make([]string, 0, len(infos))
	for _, info := range infos {
		names = append(names, info.Name)
	}
	t.listed, t.listedAt = names, time.Now()
	return t.listed, nil
}

// load reads the current record of the shard and its revision, 0 if it has none.
func (t *Table) load(ctx context.Context, shard int) (Record, uint64, error) {
	e, err := t.kv.Get(ctx, key(shard))
	if err != nil {
		if err == jetstream.ErrKeyNotFound {
			return Record{}, 0, nil
		}
		return Record{}, 0, err
	}
	var r Record
	if err := json.Unmarshal(e.Value(), &r); err != nil {
		return Record{}, 0, fmt.Errorf("decoding the record of shard %d: %w", shard, err)
	}
	return r, e.Revision(), nil
}

// swap writes the record if the shard's revision is still rev, and returns the new revision.
func (t *Table) swap(ctx context.Context, shard int, r Record, rev uint64) (uint64, error) {
	data, err := json.Marshal(r)
	if err != nil {
		return 0, err
	}
	if rev == 0 {
		return t.kv.Create(ctx, key(shard), data)
	}
	return t.kv.Update(ctx, key(shard), data, rev)
}

func (t *Table) watch(ctx context.Context, w jetstream.KeyWatcher, ready chan struct{}) {
	defer func() {
		if err := w.Stop(); err != nil && ctx.Err() == nil {
			log.Warn(ctx, "stopping the shards watcher failed", "cause", err)
		}
	}()
	for {
		select {
		case <-ctx.Done():
			return
		case e, ok := <-w.Updates():
			if !ok {
				return
			}
			if e == nil {
				close(ready)
				continue
			}
			t.apply(ctx, e)
		}
	}
}

func (t *Table) apply(ctx context.Context, e jetstream.KeyValueEntry) {
	t.mu.Lock()
	defer t.mu.Unlock()
	switch e.Operation() {
	case jetstream.KeyValueDelete, jetstream.KeyValuePurge:
		delete(t.records, e.Key())
	default:
		var r Record
		if err := json.Unmarshal(e.Value(), &r); err != nil {
			log.Warn(ctx, "invalid shard record", "key", e.Key(), "cause", err)
			return
		}
		t.records[e.Key()] = r
	}
	for _, ch := range t.subs {
		select {
		case ch <- struct{}{}:
		default:
		}
	}
}
