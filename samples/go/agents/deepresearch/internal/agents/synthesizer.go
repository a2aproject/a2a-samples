package agents

import (
	"github.com/a2aproject/a2a-go/v2/a2asrv"

	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model"
)

// NewSynthesizer creates a synthesizer agent that merges research findings into a final report.
func NewSynthesizer(tl TaskLoader, model model.LLM) (a2asrv.AgentExecutor, error) {
	a, err := llmagent.New(llmagent.Config{
		Name:        "synthesizer",
		Model:       model,
		Description: "Synthesizes research findings into a comprehensive, well-structured final report.",
		Instruction: `You are an expert research writer. You will receive findings from multiple research tasks covering different aspects of a topic.

Produce a single, comprehensive report that:
1. Opens with an executive summary of key findings.
2. Organizes the body into logical thematic sections, not by source.
3. Reconciles conflicting information — when sources disagree, present both sides and state which is better supported and why.
4. Cites sources inline using the URLs from the research findings.
5. Closes with a conclusion that highlights the most important takeaways and any remaining open questions.

Write in a clear, professional tone. Avoid redundancy — do not repeat the same finding from multiple sources. Prefer depth over breadth.`,
	})
	if err != nil {
		return nil, err
	}
	return &referencedTaskLoader{loader: tl, AgentExecutor: newExecutorFrom(a)}, nil
}
