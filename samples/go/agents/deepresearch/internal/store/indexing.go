// Package store provides MySQL-backed task persistence with event sourcing and a transactional outbox.
package store

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/a2asrv/taskstore"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
)

// Index provides MySQL-based task indexing for fast lookups and listing.
type Index struct {
	db *sql.DB
}

// IndexQueryParams specifies filters and pagination for task listing.
type IndexQueryParams struct {
	ContextID    string
	State        a2a.TaskState
	UpdatedAfter *time.Time
	PageSize     int
	PageToken    string
}

// IndexQueryResult holds a page of indexed tasks and pagination metadata.
type IndexQueryResult struct {
	Tasks         []*IndexedTask
	TotalSize     int
	NextPageToken string
}

// IndexedTask is a lightweight task record stored in the MySQL index.
type IndexedTask struct {
	ID        a2a.TaskID
	State     a2a.TaskState
	User      string
	Agent     domain.AgentType
	Version   taskstore.TaskVersion
	ContextID string
}

// NewIndex creates an [Index] backed by the given database connection.
func NewIndex(db *sql.DB) *Index {
	return &Index{db}
}

// Insert adds a new task to the index within the given transaction.
func (*Index) Insert(ctx context.Context, tx *sql.Tx, task *a2a.Task) (taskstore.TaskVersion, error) {
	user := "anonymous"
	if callCtx, ok := a2asrv.CallContextFrom(ctx); ok {
		user = callCtx.User.Name
	}
	info := domain.NodeInfoFrom(ctx)
	version := taskstore.TaskVersion(1)
	_, err := tx.ExecContext(ctx, `
		INSERT INTO tasks (task_id, context_id, state, user, agent, version)
		VALUES (?, ?, ?, ?, ?, ?)
	`, string(task.ID), task.ContextID, string(task.Status.State), user, info.Agent, version)
	if err != nil {
		return 0, err
	}
	return version, nil
}

// Update bumps the task version and state within the given transaction. Returns [taskstore.ErrConcurrentModification] on conflict.
func (*Index) Update(ctx context.Context, tx *sql.Tx, task *a2a.Task, prevVersion taskstore.TaskVersion) (taskstore.TaskVersion, error) {
	res, err := tx.ExecContext(ctx,
		`UPDATE tasks SET state = ?, version = ? WHERE task_id = ? AND version = ?`,
		task.Status.State, int64(prevVersion)+1, task.ID, int64(prevVersion),
	)
	if err != nil {
		return 0, fmt.Errorf("update task: %w", err)
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return 0, fmt.Errorf("rows affected: %w", err)
	}
	if affected == 0 {
		return 0, taskstore.ErrConcurrentModification
	}
	return prevVersion + 1, nil
}

// QueryByID returns indexed tasks matching the given IDs.
func (s *Index) QueryByID(ctx context.Context, ids []a2a.TaskID) ([]*IndexedTask, error) {
	if len(ids) == 0 {
		return nil, nil
	}
	args := make([]any, len(ids))
	placeholders := make([]string, len(ids))
	for i, id := range ids {
		placeholders[i] = "?"
		args[i] = id
	}
	query := fmt.Sprintf("WHERE `task_id` IN (%s)", strings.Join(placeholders, ","))
	tasks, err := s.rawQuery(ctx, rawQueryParts{where: query}, args)
	if err != nil {
		return nil, fmt.Errorf("query failed: %w", err)
	}
	return tasks, nil
}

// Query returns a paginated list of indexed tasks matching the given filters.
func (s *Index) Query(ctx context.Context, req *IndexQueryParams) (*IndexQueryResult, error) {
	if req.PageSize > 1000 {
		return nil, fmt.Errorf("page size must be <= 1000")
	}
	pageSize := 10
	if req.PageSize > 0 {
		pageSize = req.PageSize
	}

	where := "WHERE 1=1"
	args := []any{}
	if req.ContextID != "" {
		where += " AND `context_id` = ?"
		args = append(args, req.ContextID)
	}
	if req.State != a2a.TaskStateUnspecified {
		where += " AND `status` = ?"
		args = append(args, string(req.State))
	}
	if req.UpdatedAfter != nil {
		where += " AND `updated_at` >= ?"
		args = append(args, *req.UpdatedAfter)
	}

	var totalSize int
	if err := s.db.QueryRowContext(ctx, "SELECT COUNT(*) FROM tasks "+where, args...).Scan(&totalSize); err != nil {
		return nil, fmt.Errorf("count: %w", err)
	}
	offset := 0
	if req.PageToken != "" {
		if _, err := fmt.Sscanf(req.PageToken, "%d", &offset); err != nil {
			return nil, fmt.Errorf("invalid page token: %w", a2a.ErrInvalidRequest)
		}
	}
	args = append(args, pageSize, offset)

	tasks, err := s.rawQuery(ctx, rawQueryParts{where: where, limit: "LIMIT ?", offset: "OFFSET ?"}, args)
	if err != nil {
		return nil, fmt.Errorf("query failed: %w", err)
	}

	var nextPageToken string
	if nextOffset := offset + pageSize; nextOffset < totalSize {
		nextPageToken = fmt.Sprintf("%d", nextOffset)
	}

	return &IndexQueryResult{
		Tasks:         tasks,
		TotalSize:     totalSize,
		NextPageToken: nextPageToken,
	}, nil
}

type rawQueryParts struct {
	where  string
	limit  string
	offset string
}

func (s *Index) rawQuery(ctx context.Context, rqp rawQueryParts, args []any) ([]*IndexedTask, error) {
	parts := []string{"SELECT `task_id`, `state`, `user`, `agent`, `version`, `context_id` FROM `tasks`"}
	for _, op := range []string{rqp.where, rqp.limit, rqp.offset} {
		if op != "" {
			parts = append(parts, op)
		}
	}

	rows, err := s.db.QueryContext(ctx, strings.Join(parts, " "), args...)
	if err != nil {
		return nil, fmt.Errorf("query tasks: %w", err)
	}
	defer rows.Close()

	var tasks []*IndexedTask
	for rows.Next() {
		var task IndexedTask
		if err := rows.Scan(&task.ID, &task.State, &task.User, &task.Agent, &task.Version, &task.ContextID); err != nil {
			return nil, fmt.Errorf("scan failed: %w", err)
		}
		tasks = append(tasks, &task)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows: %w", err)
	}

	return tasks, nil
}
