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
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/lease"
)

// OutboxConfig configures the transactional outbox relay.
type OutboxConfig struct {
	DB     *sql.DB
	Agent  domain.AgentType
	Writer eventqueue.Writer

	LeaseManager *lease.Manager
	Interval     time.Duration
}

// Outbox implements a transactional outbox that atomically persists events with task state and relays them to NATS.
type Outbox struct {
	cfg       OutboxConfig
	agentType string
}

// NewOutbox creates a new [Outbox] with the given configuration.
func NewOutbox(cfg OutboxConfig) (*Outbox, error) {
	if cfg.Interval <= 0 {
		return nil, fmt.Errorf("outbox polling interval must be > 0")
	}
	return &Outbox{
		cfg:       cfg,
		agentType: string(cfg.Agent),
	}, nil
}

// Insert writes an event to the outbox table within the given transaction.
func (r *Outbox) Insert(ctx context.Context, tx *sql.Tx, msg *eventqueue.Message) error {
	tid := msg.Event.TaskInfo().TaskID
	eventData, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("marshal event: %w", err)
	}

	_, err = tx.ExecContext(ctx, `INSERT INTO outbox (task_id, agent, event_data) VALUES (?, ?, ?)`, string(tid), r.agentType, eventData)
	if err != nil {
		return fmt.Errorf("outbox insert: %w", err)
	}
	return nil
}

// Run starts the leader-elected polling loop that relays outbox rows to NATS.
func (r *Outbox) Run(ctx context.Context) error {
	leaseKey := r.agentType + "-leader"
	lm := r.cfg.LeaseManager
	defer lm.ReleaseAll(ctx)

	for ctx.Err() == nil {
		lease, err := lm.Acquire(ctx, leaseKey, r.agentType)
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
			if err := lease.Renew(ctx); err != nil {
				log.Error(ctx, "outbox lease renewal failed", err)
				break
			}
			time.Sleep(r.cfg.Interval)
		}
	}
	return ctx.Err()
}

func (r *Outbox) poll(ctx context.Context) error {
	rows, err := r.cfg.DB.QueryContext(ctx, `SELECT id, event_data FROM outbox WHERE agent = ? ORDER BY id ASC LIMIT 100`, r.agentType)
	if err != nil {
		return err
	}
	defer rows.Close()

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
