package agents

import (
	"context"
	"encoding/json"
	"fmt"
	"slices"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/nats-io/nats.go/jetstream"
)

type stageType string

const (
	stageResearch  stageType = "planning"
	stageAnalysis  stageType = "analysis"
	stageSynthesiz stageType = "synthesiz"
)

type taskState struct {
	ID    a2a.TaskID
	State a2a.TaskState
}

type messagePrepare struct {
	Type        stageType      `json:"type"`
	Messages    []*a2a.Message `json:"messages"`
	PrevStageID string         `json:"prevStageId"`
}

type messageCommit struct {
	TaskIDs []a2a.TaskID `json:"taskIds"`
}

type orchestratorEvent struct {
	StageID        string                     `json:"stageId"`
	StatusUpdate   *a2a.TaskStatusUpdateEvent `json:"statusUpdate,omitempty"`
	MessagePrepare *messagePrepare            `json:"messagePrepare,omitempty"`
	MessageCommit  *messageCommit             `json:"messageCommit,omitempty"`
}

func parseOrchestratorEvent(_ context.Context, msg jetstream.Msg) (*orchestratorEvent, error) {
	var event orchestratorEvent
	if err := json.Unmarshal(msg.Data(), &event); err != nil {
		return nil, err
	}
	if event.StatusUpdate != nil {
		event.StageID = msg.Headers().Get("A2A-Token")
	}
	return &event, nil
}

type deepresearchStage struct {
	id            string
	message       *messagePrepare
	messageCommit *messageCommit
	tasks         map[a2a.TaskID]a2a.TaskState
}

func (p *deepresearchStage) taskID() (a2a.TaskID, error) {
	if len(p.tasks) != 1 {
		return "", fmt.Errorf("taskID() is only valid for single-task stages (analysis, synthesis)")
	}
	for tid := range p.tasks {
		return tid, nil
	}
	return "", nil
}

func (p *deepresearchStage) finished() bool {
	if len(p.tasks) < len(p.message.Messages) {
		return false
	}
	for _, state := range p.tasks {
		if !state.Terminal() {
			return false
		}
	}
	return true
}

type orchestratorState struct {
	stages        []*deepresearchStage
	summarization *taskState
}

func (s *orchestratorState) previousStage(stage *deepresearchStage) *deepresearchStage {
	if stage == nil || stage.message.PrevStageID == "" {
		return nil
	}
	si := slices.IndexFunc(s.stages, func(ds *deepresearchStage) bool {
		return ds.id == stage.message.PrevStageID
	})
	return s.stages[si]
}

func (s *orchestratorState) activeStage() *deepresearchStage {
	if len(s.stages) == 0 {
		return nil
	}
	return s.stages[len(s.stages)-1]
}

func evolveOrchestratorState(_ context.Context, s *orchestratorState, event *orchestratorEvent) error {
	if event.MessagePrepare != nil {
		s.stages = append(s.stages, &deepresearchStage{
			id:      event.StageID,
			message: event.MessagePrepare,
			tasks:   make(map[a2a.TaskID]a2a.TaskState),
		})
		return nil
	}

	stageIndex := slices.IndexFunc(s.stages, func(stage *deepresearchStage) bool {
		return stage.id == event.StageID
	})
	if stageIndex < 0 {
		return fmt.Errorf("event for unknown stage %q", event.StageID)
	}

	if event.MessageCommit != nil {
		s.stages[stageIndex].messageCommit = event.MessageCommit
		return nil
	}

	tu := event.StatusUpdate
	stage := s.stages[stageIndex]
	if _, ok := stage.tasks[tu.TaskID]; !ok && len(stage.tasks) >= len(stage.message.Messages) {
		return fmt.Errorf("more tasks than messages for stage %q", event.StageID)
	}
	stage.tasks[tu.TaskID] = tu.Status.State
	return nil
}
