package agents

import (
	"context"
	"errors"
	"fmt"
	"iter"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/google/uuid"
	"github.com/nats-io/nats.go/jetstream"

	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/cluster"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/msgstream"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/statemachine"

	"google.golang.org/adk/model"
	"google.golang.org/adk/server/adka2a/v2"
	"google.golang.org/genai"
)

const (
	statesStream  = "STATES"
	statesSubject = "states"
)

// OrchestratorConfig configures an orchestrator agent.
type OrchestratorConfig struct {
	JS          jetstream.JetStream
	ReportStore a2a.URL
	Researcher  *cluster.Client
	Analyzer    *cluster.Client
	Synthesizer *cluster.Client
	Model       model.LLM
}

// CreateOrchestrator creates and returns the orchestrator agent executor.
func CreateOrchestrator(ctx context.Context, cfg OrchestratorConfig) (a2asrv.AgentExecutor, error) {
	stream, err := cfg.JS.Stream(ctx, statesStream)
	if err != nil {
		return nil, fmt.Errorf("states stream init failed: %w", err)
	}
	return &orchestrator{OrchestratorConfig: cfg, stream: stream}, nil
}

type orchestrator struct {
	OrchestratorConfig
	stream jetstream.Stream
}

// Execute implements [a2asrv.AgentExecutor.Execute].
func (o *orchestrator) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		exec := &orchestratorRun{
			execCtx:   execCtx,
			model:     o.Model,
			jetstream: o.JS,
			subject:   statesSubject + "." + string(execCtx.TaskID),
			state:     &orchestratorState{},
			yield: func(e a2a.Event, err error) bool {
				log.Info(ctx, "orcherstrator yield", "type", fmt.Sprintf("%T", e), "error", err)
				return yield(e, err)
			},
		}

		if !exec.yield(a2a.NewSubmittedTask(execCtx, execCtx.Message), nil) {
			return
		}

		err := statemachine.Run(ctx, o.stream, statemachine.Spec[*orchestratorEvent, *orchestratorState]{
			Subject: exec.subject,
			State:   exec.state,
			Decode:  parseOrchestratorEvent,
			Evolve:  evolveOrchestratorState,
			Act: func(ctx context.Context, s *orchestratorState, events []*orchestratorEvent) error {
				stage := s.activeStage()
				switch {
				case stage == nil: // initial state
					return o.research(ctx, exec, nil)

				case stage.messageCommit == nil: // crash recovery
					return o.recoverFromFailure(ctx, exec, stage)

				case !stage.finished(): // wait for tasks to complete
					return nil

				default:
					return o.runNextStage(ctx, exec, stage)
				}
			},
		})
		if err != nil {
			if !errors.Is(err, statemachine.ErrStopped) {
				exec.yield(nil, err)
			}
		}
	}
}

// Cancel implements [a2asrv.AgentExecutor.Cancel].
func (o *orchestrator) Cancel(_ context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		yield(a2a.NewStatusUpdateEvent(
			execCtx,
			a2a.TaskStateCanceled,
			a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart("cancelled")),
		), nil)
	}
}

// recoverFromFailure is called for a stage with messageCommit equal to nil. This can happen when either
// a message sneding or messageCommit publishing failed and executor got restarted.
func (o *orchestrator) recoverFromFailure(ctx context.Context, exec *orchestratorRun, stage *deepresearchStage) error {
	if sendMaybeFailed := len(stage.tasks) < len(stage.message.Messages); sendMaybeFailed {
		return o.runNextStage(ctx, exec, exec.state.previousStage(stage))
	}
	allDone := false
	for _, state := range stage.tasks {
		if !state.Terminal() {
			allDone = false
			break
		}
	}
	if allDone {
		return o.runNextStage(ctx, exec, stage)
	}
	return nil // wait for task completions
}

func (o *orchestrator) runNextStage(ctx context.Context, exec *orchestratorRun, stage *deepresearchStage) error {
	switch stage.message.Type {
	case stageResearch:
		if stage.message.PrevStageID == "" { // analyze initial research findings
			return o.analyze(ctx, exec, stage)
		} else { // follow-up research finished, synthesize all findings
			return o.synthesize(ctx, exec)
		}
	case stageAnalysis: // start follow-up research
		return o.research(ctx, exec, stage)
	case stageSynthesiz: // deliver final result
		return o.complete(ctx, exec, stage)
	default:
		return fmt.Errorf("unknown uncommited stage %q", stage.message.Type)
	}
}

func (o *orchestrator) research(ctx context.Context, e *orchestratorRun, prevStage *deepresearchStage) error {
	if !e.updateStatus("Planning research...") {
		return statemachine.ErrStopped
	}

	var parts []*a2a.Part
	if prevStage == nil {
		parts = e.execCtx.Message.Parts
	} else {
		prevTaskID, err := prevStage.taskID()
		if err != nil {
			return err
		}
		aParts, err := o.Analyzer.GetArtifactParts(ctx, prevTaskID)
		if err != nil {
			return err
		}
		parts = aParts
	}

	converted, err := adka2a.ToGenAIParts(parts)
	if err != nil {
		return fmt.Errorf("plan input conversion: %w", err)
	}

	plan, err := runPlanner(ctx, e.model, genai.NewContentFromParts(converted, genai.RoleUser))
	if err != nil {
		return fmt.Errorf("planner: %w", err)
	}

	if !e.yieldArtifact(a2a.NewTextPart(plan.Summary)) {
		return statemachine.ErrStopped
	}

	messages := make([]*a2a.Message, len(plan.Subtasks))
	for i, st := range plan.Subtasks {
		messages[i] = a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(st))
	}

	var prevStageID string
	if prevStage != nil {
		prevStageID = prevStage.id
	}
	if err := e.send(ctx, o.Researcher, stageResearch, prevStageID, messages); err != nil {
		return fmt.Errorf("research failed: %w", err)
	}
	for _, subtask := range plan.Subtasks {
		if !e.updateStatus(fmt.Sprintf("Researching %q", subtask)) {
			return statemachine.ErrStopped
		}
	}
	return nil
}

func (o *orchestrator) analyze(ctx context.Context, e *orchestratorRun, prevStage *deepresearchStage) error {
	if !e.updateStatus("Analyzing findings...") {
		return statemachine.ErrStopped
	}
	message := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("Find contradictions and controversial parts in these research findings."))
	for tid := range prevStage.tasks {
		message.ReferenceTasks = append(message.ReferenceTasks, tid)
	}
	return e.send(ctx, o.Analyzer, stageAnalysis, prevStage.id, []*a2a.Message{message})
}

func (o *orchestrator) synthesize(ctx context.Context, e *orchestratorRun) error {
	if !e.updateStatus("Synthesizing final report...") {
		return statemachine.ErrStopped
	}
	message := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("Synthesize all the research findings into the final report."))
	for stage := e.state.activeStage(); stage != nil; stage = e.state.previousStage(stage) {
		if stage.message.Type == stageResearch {
			for tid := range stage.tasks {
				message.ReferenceTasks = append(message.ReferenceTasks, tid)
			}
		}
	}
	return e.send(ctx, o.Synthesizer, stageSynthesiz, e.state.activeStage().id, []*a2a.Message{message})
}

func (o *orchestrator) complete(_ context.Context, e *orchestratorRun, stage *deepresearchStage) error {
	reportID, err := stage.taskID()
	if err != nil {
		return fmt.Errorf("report not ready: %w", err)
	}
	url := o.ReportStore + a2a.URL("/reports/"+reportID)
	if !e.yieldArtifact(a2a.NewTextPart("Your report is ready for review."), a2a.NewFileURLPart(url, "text/html")) {
		return statemachine.ErrStopped
	}
	e.complete()
	return statemachine.ErrStopped
}

type orchestratorRun struct {
	model model.LLM

	execCtx *a2asrv.ExecutorContext
	yield   func(a2a.Event, error) bool

	jetstream jetstream.JetStream
	subject   string

	state *orchestratorState
}

func (r *orchestratorRun) send(ctx context.Context, client *cluster.Client, st stageType, prevStageID string, messages []*a2a.Message) error {
	stageID := uuid.NewString()
	prepareEvent := &orchestratorEvent{StageID: stageID, MessagePrepare: &messagePrepare{Type: st, Messages: messages, PrevStageID: prevStageID}}
	if err := msgstream.PublishJSON(ctx, r.jetstream, r.subject, prepareEvent); err != nil {
		return fmt.Errorf("prepare publish: %w", err)
	}
	taskIDs, err := client.SendAll(ctx, r.execCtx, messages, msgstream.NewPushConfig(r.subject, stageID))
	if err != nil {
		return fmt.Errorf("send all: %w", err)
	}
	commitEvent := &orchestratorEvent{StageID: stageID, MessageCommit: &messageCommit{TaskIDs: taskIDs}}
	if err := msgstream.PublishJSON(ctx, r.jetstream, r.subject, commitEvent); err != nil {
		return fmt.Errorf("commit publish: %w", err)
	}
	return nil
}

func (r *orchestratorRun) updateStatus(text string) bool {
	return r.yield(a2a.NewStatusUpdateEvent(
		r.execCtx, a2a.TaskStateWorking, a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(text)),
	), nil)
}

func (r *orchestratorRun) yieldArtifact(parts ...*a2a.Part) bool {
	artifact := a2a.NewArtifactEvent(r.execCtx, parts...)
	artifact.LastChunk = true
	return r.yield(artifact, nil)
}

func (r *orchestratorRun) complete() {
	_ = r.yield(a2a.NewStatusUpdateEvent(r.execCtx, a2a.TaskStateCompleted, nil), nil)
}
