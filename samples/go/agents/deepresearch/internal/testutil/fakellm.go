// Package drtest provides reusable test helpers for the deep research system.
package testutil

import (
	"context"
	"iter"

	"google.golang.org/adk/model"
	"google.golang.org/genai"
)

// FakeLLM implements [model.LLM] with canned responses. When the request
// carries a ResponseSchema (the planner call) it returns a two-subtask
// research plan JSON; otherwise it returns a plain-text answer.
type FakeLLM struct{}

var _ model.LLM = (*FakeLLM)(nil)

// Name implements [model.LLM.Name].
func (*FakeLLM) Name() string { return "fake-llm" }

// GenerateContent implements [model.LLM.GenerateContent].
func (*FakeLLM) GenerateContent(_ context.Context, req *model.LLMRequest, _ bool) iter.Seq2[*model.LLMResponse, error] {
	return func(yield func(*model.LLMResponse, error) bool) {
		text := "Fake research finding."
		if req.Config != nil && req.Config.ResponseSchema != nil {
			text = `{"summary":"Test plan","subtasks":["Subtask A","Subtask B"]}`
		}
		yield(&model.LLMResponse{
			Content: &genai.Content{
				Parts: []*genai.Part{{Text: text}},
				Role:  "model",
			},
		}, nil)
	}
}
