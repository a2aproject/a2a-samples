package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2asrv/eventqueue"
	"github.com/a2aproject/a2a-go/v2/log"
)

// Leader elects the server that relays the outbox, for example the lease
// manager of the nats integration.
type Leader interface {
	// Lead blocks until the caller holds key, and returns the func that renews it.
	Lead(ctx context.Context, key, holder string) (renew func(context.Context) error, err error)
	// ReleaseAll releases the keys the caller holds.
	ReleaseAll(ctx context.Context)
}

// OutboxConfig configures the transactional outbox relay.
type OutboxConfig struct {
	DB *sql.DB
	// Partition separates the rows of agents that share the database. Each
	// partition has its own relay.
	Partition string
	Writer    eventqueue.Writer

	Leader   Leader
	Interval time.Duration
}

// Outbox implements a transactional outbox that atomically persists events with task state and relays them to NATS.
type Outbox struct {
	cfg OutboxConfig
}

// NewOutbox creates a new [Outbox] with the given configuration.
func NewOutbox(cfg OutboxConfig) (*Outbox, error) {
	if cfg.Interval <= 0 {
		return nil, fmt.Errorf("outbox polling interval must be > 0")
	}
	return &Outbox{cfg: cfg}, nil
}

// Insert writes an event to the outbox table within the given transaction.
func (r *Outbox) Insert(ctx context.Context, tx *sql.Tx, msg *eventqueue.Message) error {
	tid := msg.Event.TaskInfo().TaskID
	eventData, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("marshal event: %w", err)
	}

	_, err = tx.ExecContext(ctx, `INSERT INTO outbox (task_id, agent, event_data) VALUES (?, ?, ?)`, string(tid), r.cfg.Partition, eventData)
	if err != nil {
		return fmt.Errorf("outbox insert: %w", err)
	}
	return nil
}

// Run starts the leader-elected polling loop that relays outbox rows to NATS.
func (r *Outbox) Run(ctx context.Context) error {
	leaderKey := r.cfg.Partition + "-leader"
	defer r.cfg.Leader.ReleaseAll(ctx)

	for ctx.Err() == nil {
		renew, err := r.cfg.Leader.Lead(ctx, leaderKey, r.cfg.Partition)
		if errors.Is(err, context.Canceled) {
			break
		}
		if err != nil {
			log.Error(ctx, "outbox lease acquire failed, retrying", err)
			time.Sleep(r.cfg.Interval)
			continue
		}
		for {
			err := r.poll(ctx)
			if errors.Is(err, context.Canceled) {
				break
			}
			if err != nil {
				log.Warn(ctx, "outbox poll failed", err)
			}
			if err := renew(ctx); err != nil {
				log.Error(ctx, "outbox lease renewal failed", err)
				break
			}
			time.Sleep(r.cfg.Interval)
		}
	}
	return ctx.Err()
}

func (r *Outbox) poll(ctx context.Context) error {
	rows, err := r.cfg.DB.QueryContext(ctx, `SELECT id, event_data FROM outbox WHERE agent = ? ORDER BY id ASC LIMIT 100`, r.cfg.Partition)
	if err != nil {
		return err
	}
	defer func() { _ = rows.Close() }()

	for rows.Next() {
		var (
			id        int64
			eventData []byte
		)
		if err := rows.Scan(&id, &eventData); err != nil {
			return err
		}

		var message eventqueue.Message
		if err := json.Unmarshal(eventData, &message); err != nil {
			log.Error(ctx, "outbox: invalid event data, deleting", err, "outbox_id", id)
			r.delete(ctx, id)
			continue
		}

		tid := message.Event.TaskInfo().TaskID
		if err := r.cfg.Writer.Write(ctx, &message); err != nil {
			log.Warn(ctx, "outbox: publish failed, will retry", err, "outbox_id", id, "task_id", tid)
			continue
		}

		r.delete(ctx, id)

		log.Debug(ctx, "outbox event relayed", "outbox_id", id, "task_id", tid)
	}

	return rows.Err()
}

func (r *Outbox) delete(ctx context.Context, id int64) {
	if _, err := r.cfg.DB.ExecContext(ctx, `DELETE FROM outbox WHERE id = ?`, id); err != nil {
		log.Error(ctx, "outbox: delete failed", err, "outbox_id", id)
	}
}
