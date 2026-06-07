package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"maps"
	"slices"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv/eventqueue"
	"github.com/a2aproject/a2a-go/v2/a2asrv/taskstore"
	"github.com/a2aproject/a2a-go/v2/log"
	"golang.org/x/sync/errgroup"
)

// Config holds dependencies for the task [Store].
type Config struct {
	DB          *sql.DB
	Outbox      *Outbox
	TaskIndex   *Index
	EventReplay eventqueue.Manager
}

// Store implements [taskstore.Store] using MySQL for indexing and NATS event replay for materialization.
type Store struct {
	Config
}

var _ taskstore.Store = (*Store)(nil)

// New creates a new task [Store].
func New(cfg Config) *Store {
	return &Store{cfg}
}

// Create persists a new task and publishes its creation event via the outbox.
func (s *Store) Create(ctx context.Context, task *a2a.Task) (taskstore.TaskVersion, error) {
	tx, err := s.DB.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	version, err := s.TaskIndex.Insert(ctx, tx, task)
	if err != nil {
		return 0, fmt.Errorf("task index update: %w", err)
	}

	msg := &eventqueue.Message{Event: task, Protocol: a2a.Version, TaskVersion: version}
	if err := s.Outbox.Insert(ctx, tx, msg); err != nil {
		return 0, fmt.Errorf("txn event send: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit: %w", err)
	}

	log.Debug(ctx, "task created", "task_id", task.ID)

	return version, nil
}

// Update applies a state change to an existing task and publishes the event via the outbox.
func (s *Store) Update(ctx context.Context, req *taskstore.UpdateRequest) (taskstore.TaskVersion, error) {
	tx, err := s.DB.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	newVersion, err := s.TaskIndex.Update(ctx, tx, req.Task, req.PrevVersion)
	if err != nil {
		return 0, fmt.Errorf("task index update: %w", err)
	}

	msg := &eventqueue.Message{Event: req.Event, Protocol: a2a.Version, TaskVersion: newVersion}
	if err := s.Outbox.Insert(ctx, tx, msg); err != nil {
		return 0, fmt.Errorf("event outbox: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit: %w", err)
	}

	log.Debug(ctx, "task updated", "task_id", req.Task.ID, "version", newVersion)

	return newVersion, nil
}

func (s *Store) GetIndexed(ctx context.Context, tid a2a.TaskID) (*IndexedTask, error) {
	indexed, err := s.TaskIndex.QueryByID(ctx, []a2a.TaskID{tid})
	if err != nil {
		return nil, err
	}
	if len(indexed) == 0 {
		return nil, a2a.ErrTaskNotFound
	}
	return indexed[0], nil
}

// Get materializes a task by replaying its events from the stream.
func (s *Store) Get(ctx context.Context, tid a2a.TaskID) (*taskstore.StoredTask, error) {
	indexed, err := s.TaskIndex.QueryByID(ctx, []a2a.TaskID{tid})
	if err != nil {
		return nil, err
	}
	if len(indexed) == 0 {
		return nil, a2a.ErrTaskNotFound
	}
	task, err := s.materialize(ctx, tid, indexed[0].Version)
	if err != nil {
		return nil, err
	}
	return &taskstore.StoredTask{Task: task, Version: indexed[0].Version}, nil
}

// List returns a paginated list of tasks matching the request filters.
func (s *Store) List(ctx context.Context, req *a2a.ListTasksRequest) (*a2a.ListTasksResponse, error) {
	pageSize := 10
	if req.PageSize > 0 && req.PageSize < pageSize {
		pageSize = req.PageSize
	}
	queryResult, err := s.TaskIndex.Query(ctx, &IndexQueryParams{
		ContextID:    req.ContextID,
		State:        req.Status,
		UpdatedAfter: req.StatusTimestampAfter,
		PageToken:    req.PageToken,
		PageSize:     pageSize,
	})
	if err != nil {
		return nil, err
	}
	tasks, err := s.materializeAll(ctx, queryResult.Tasks)
	if err != nil {
		return nil, err
	}
	var filtered []*a2a.Task
	for _, task := range tasks {
		if !req.IncludeArtifacts {
			task.Artifacts = nil
		}
		if req.HistoryLength != nil && len(task.History) > *req.HistoryLength {
			task.History = task.History[len(task.History)-*req.HistoryLength:]
		}
		filtered = append(filtered, task)
	}
	return &a2a.ListTasksResponse{
		Tasks:         filtered,
		PageSize:      len(filtered),
		TotalSize:     queryResult.TotalSize,
		NextPageToken: queryResult.NextPageToken,
	}, nil
}

// Load implements [agents.TaskLoader].
func (s *Store) Load(ctx context.Context, ids []a2a.TaskID) ([]*a2a.Task, error) {
	indexed, err := s.TaskIndex.QueryByID(ctx, ids)
	if err != nil {
		return nil, err
	}
	return s.materializeAll(ctx, indexed)
}

func (s *Store) materializeAll(ctx context.Context, indexedTasks []*IndexedTask) ([]*a2a.Task, error) {
	var group errgroup.Group
	taskChan := make(chan *a2a.Task, len(indexedTasks))
	for _, indexedTask := range indexedTasks {
		group.Go(func() error {
			task, err := s.materialize(ctx, indexedTask.ID, indexedTask.Version)
			if err != nil {
				return fmt.Errorf("task loading failed: %w", err)
			}
			taskChan <- task
			return nil
		})
	}
	if err := group.Wait(); err != nil {
		return nil, err
	}
	close(taskChan)

	tasks := make([]*a2a.Task, 0, len(indexedTasks))
	for task := range taskChan {
		tasks = append(tasks, task)
	}
	return tasks, nil
}

// materialize uses eventReplay to produce a task state.
func (s *Store) materialize(ctx context.Context, tid a2a.TaskID, v taskstore.TaskVersion) (*a2a.Task, error) {
	reader, err := s.EventReplay.CreateReader(ctx, tid)
	if err != nil {
		return nil, fmt.Errorf("event replay initiation: %w", err)
	}
	defer reader.Close()

	task := &a2a.Task{}
	for {
		msg, err := reader.Read(ctx)
		if errors.Is(err, eventqueue.ErrQueueClosed) {
			break
		}
		if err != nil {
			return nil, err
		}
		if msg.TaskVersion.After(v) {
			break
		}
		switch tv := msg.Event.(type) {
		case *a2a.Task:
			task = tv
		case *a2a.TaskStatusUpdateEvent:
			applyStatusUpdate(task, tv)
		case *a2a.TaskArtifactUpdateEvent:
			task.Artifacts = applyArtifactUpdate(task.Artifacts, tv)
		}
		if msg.TaskVersion == v {
			break
		}
	}
	return task, nil
}

func applyStatusUpdate(task *a2a.Task, event *a2a.TaskStatusUpdateEvent) {
	if task.Status.Message != nil {
		task.History = append(task.History, task.Status.Message)
	}
	task.Status = event.Status
	if task.Metadata == nil {
		task.Metadata = event.Metadata
	} else {
		maps.Copy(task.Metadata, event.Metadata)
	}
}

func applyArtifactUpdate(artifacts []*a2a.Artifact, event *a2a.TaskArtifactUpdateEvent) []*a2a.Artifact {
	updateIdx := slices.IndexFunc(artifacts, func(a *a2a.Artifact) bool {
		return a.ID == event.Artifact.ID
	})
	if updateIdx < 0 {
		return append(artifacts, event.Artifact)
	}
	if event.Append {
		artifacts[updateIdx].Parts = append(artifacts[updateIdx].Parts, event.Artifact.Parts...)
	} else {
		artifacts[updateIdx] = event.Artifact
	}
	return artifacts
}
