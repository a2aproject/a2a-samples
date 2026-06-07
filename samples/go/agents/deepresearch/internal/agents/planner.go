package agents

import (
	"context"
	"encoding/json"
	"fmt"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model"
	"google.golang.org/adk/runner"
	"google.golang.org/adk/session"
	"google.golang.org/genai"
)

type researchPlan struct {
	Summary  string   `json:"summary"`
	Subtasks []string `json:"subtasks"`
}

var researchPlanSchema = &genai.Schema{
	Type: genai.TypeObject,
	Properties: map[string]*genai.Schema{
		"summary": {Type: genai.TypeString, Description: "Brief summary of the research plan."},
		"subtasks": {
			Type:        genai.TypeArray,
			Items:       &genai.Schema{Type: genai.TypeString},
			Description: "Focused subtasks that can be researched independently.",
		},
	},
	Required: []string{"summary", "subtasks"},
}

func runPlanner(ctx context.Context, model model.LLM, content *genai.Content) (*researchPlan, error) {
	a, err := llmagent.New(llmagent.Config{
		Name:        "planner",
		Description: "Deep research planner agent.",
		Model:       model,
		Instruction: `You are the planning component of a multi-agent deep research system.

## How the system works
- Each subtask you produce is sent to a separate researcher agent that uses Google Search.
- Researchers work independently and cannot see each other's subtasks or results.
- After initial research, an analyzer checks for contradictions and gaps, and you may be called again with the analysis to plan targeted follow-up research.

## Planning rules
1. Produce 3–5 subtasks. Fewer for narrow topics, more for broad ones.
2. Each subtask must be self-contained — include enough context that a researcher can investigate it without seeing the original question or other subtasks.
3. Subtasks must not overlap — do not assign the same ground to multiple researchers.
4. Frame each subtask as a clear, specific research question or directive, not a vague topic label.
5. Prefer subtasks that target publicly available, searchable information.

## When handling follow-up research
If the input contains analysis of prior findings (contradictions, gaps, or open questions), focus subtasks on resolving those specific issues. Do not re-research topics already well-covered.

## Summary
Write a brief, user-facing summary (1–2 sentences) describing what the plan covers.`,
		OutputSchema: researchPlanSchema,
	})
	if err != nil {
		return nil, fmt.Errorf("llm create failed: %w", err)
	}
	sessionSvc := session.InMemoryService()
	r, err := runner.New(runner.Config{AppName: a.Name(), Agent: a, SessionService: sessionSvc})
	if err != nil {
		return nil, fmt.Errorf("runner create failed: %w", err)
	}
	sess, err := sessionSvc.Create(ctx, &session.CreateRequest{AppName: a.Name(), UserID: "user"})
	if err != nil {
		return nil, fmt.Errorf("session create failed: %w", err)
	}
	var event *session.Event
	for ev, err := range r.Run(ctx, "user", sess.Session.ID(), content, agent.RunConfig{}) {
		if err != nil {
			return nil, err
		}
		event = ev
	}
	if event == nil || event.Content == nil || len(event.Content.Parts) == 0 {
		return nil, fmt.Errorf("no content returned from planner")
	}
	var plan researchPlan
	if err := json.Unmarshal([]byte(event.Content.Parts[0].Text), &plan); err != nil {
		return nil, err
	}
	return &plan, nil
}
