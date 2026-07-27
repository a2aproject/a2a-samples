// Package lease implements distributed leader election using NATS KV.
package lease

import (
	"context"
	"errors"
	"fmt"
	"slices"
	"sync"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/nats-io/nats.go/jetstream"
)

// Manager creates and tracks distributed leases backed by a NATS KV bucket.
type Manager struct {
	kv jetstream.KeyValue

	mu     sync.Mutex
	active []*Lease
}

// CreateManager creates a [Manager] using the given KV bucket configuration.
func CreateManager(ctx context.Context, js jetstream.JetStream, cfg jetstream.KeyValueConfig) (*Manager, error) {
	kv, err := js.CreateOrUpdateKeyValue(ctx, cfg)
	if err != nil {
		if !errors.Is(err, jetstream.ErrBucketExists) {
			return nil, fmt.Errorf("create kv bucket error: %w", err)
		}
		existingKV, err := js.KeyValue(ctx, cfg.Bucket)
		if err != nil {
			return nil, fmt.Errorf("get kv bucket error: %w", err)
		}
		kv = existingKV
	}
	return &Manager{kv: kv}, nil
}

// Acquire blocks until the lease for key is obtained. It retries on contention.
func (lp *Manager) Acquire(ctx context.Context, key string, value string) (*Lease, error) {
	rawVal := []byte(value)
	for {
		rev, err := lp.kv.Create(ctx, key, rawVal)
		if err != nil && !errors.Is(err, jetstream.ErrKeyExists) {
			return nil, err
		}

		if err != nil {
			log.Info(ctx, "leader key exists, waiting for release")
			if err := lp.waitKeyDeleted(ctx, key); err != nil {
				return nil, err
			}
			continue
		}

		lease := &Lease{manager: lp, kv: lp.kv, key: key, rev: rev, value: rawVal}

		lp.mu.Lock()
		lp.active = append(lp.active, lease)
		lp.mu.Unlock()

		log.Info(ctx, "lease acquired")

		return lease, nil
	}
}

func (lp *Manager) waitKeyDeleted(ctx context.Context, key string) error {
	watcher, err := lp.kv.Watch(ctx, key)
	if err != nil {
		return err
	}
	defer func() {
		if err := watcher.Stop(); err != nil {
			log.Warn(ctx, "watcher stop failed", "cause", err)
		}
	}()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()

		case entry, ok := <-watcher.Updates():
			if !ok {
				return fmt.Errorf("unexpected watcher stop")
			}
			if entry == nil {
				continue
			}
			if entry.Operation() == jetstream.KeyValueDelete || entry.Operation() == jetstream.KeyValuePurge {
				return nil
			}
		}
	}
}

// ReleaseAll releases all active leases held by this manager.
func (lp *Manager) ReleaseAll(ctx context.Context) {
	lp.mu.Lock()
	defer lp.mu.Unlock()
	cleanupCtx := context.WithoutCancel(ctx)
	for _, lease := range lp.active {
		if err := lp.kv.Delete(cleanupCtx, lease.key, jetstream.LastRevision(lease.rev)); err != nil {
			log.Warn(ctx, "lease release failed", err, "node", string(lease.value))
		}
	}
	lp.active = nil
}

// Lease represents a single acquired distributed lock in NATS KV.
type Lease struct {
	manager *Manager
	kv      jetstream.KeyValue
	key     string
	value   []byte
	rev     uint64
}

// Renew extends the lease by updating the KV entry. Returns an error if the lease was lost.
func (l *Lease) Renew(ctx context.Context) error {
	newRev, err := l.kv.Update(ctx, l.key, l.value, l.rev)
	if err != nil {
		l.manager.mu.Lock()
		l.manager.active = slices.DeleteFunc(l.manager.active, func(another *Lease) bool { return l == another })
		l.manager.mu.Unlock()
		return fmt.Errorf("lease renewal: %w", err)
	}
	l.rev = newRev
	return nil
}
