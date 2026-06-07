package agents

import (
	"github.com/a2aproject/a2a-go/v2/a2asrv"

	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model"
)

// NewAnalyzer creates an analyzer agent that reviews research findings for contradictions and gaps.
func NewAnalyzer(tl TaskLoader, model model.LLM) (a2asrv.AgentExecutor, error) {
	a, err := llmagent.New(llmagent.Config{
		Name:        "analyzer",
		Model:       model,
		Description: "Analyzes research findings for contradictions, gaps, and areas needing follow-up.",
		Instruction: `You are a critical research analyst. You will receive a set of research findings from multiple independent research tasks.

Your job is to:
1. Identify contradictions — places where sources or findings disagree on facts, figures, or conclusions.
2. Find gaps — important aspects of the topic that the research did not cover or only mentioned superficially.
3. Assess source quality — note where findings rely on weak, outdated, or potentially biased sources.
4. Suggest follow-up questions — for each gap or contradiction, propose a specific research question that would resolve it.

Be specific: reference the exact claims that conflict, not vague generalities. Output a structured analysis with sections for contradictions, gaps, and follow-up questions.`,
	})
	if err != nil {
		return nil, err
	}
	return &referencedTaskLoader{loader: tl, AgentExecutor: newExecutorFrom(a)}, nil
}
