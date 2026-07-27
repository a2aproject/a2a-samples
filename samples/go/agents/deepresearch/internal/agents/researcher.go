package agents

import (
	"github.com/a2aproject/a2a-go/v2/a2asrv"

	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model"
	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/geminitool"
)

// NewResearcher creates a researcher agent that uses Google Search to investigate subtopics.
func NewResearcher(model model.LLM) (a2asrv.AgentExecutor, error) {
	a, err := llmagent.New(llmagent.Config{
		Name:        "researcher",
		Model:       model,
		Description: "Researches a focused subtopic using Google Search and produces a detailed, sourced report.",
		Instruction: `You are an expert research analyst. You will receive a focused research subtask.

Use Google Search to find authoritative, up-to-date information. For each claim or finding:
- Cite the source URL.
- Note the publication date when available.
- Prefer primary sources (official reports, peer-reviewed papers, authoritative organizations) over secondary coverage.

Structure your output as a coherent report with clear sections. Flag any conflicting information you encounter across sources. If a subtask is ambiguous, state your interpretation before proceeding.`,
		Tools: []tool.Tool{geminitool.GoogleSearch{}},
	})
	if err != nil {
		return nil, err
	}
	return newExecutorFrom(a), nil
}
