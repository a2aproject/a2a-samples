// Package report serves synthesizer task artifacts as styled HTML pages.
package report

import (
	"encoding/json"
	"errors"
	"html/template"
	"net/http"
	"strings"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/domain"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/store"
)

// reportData holds the template data for rendering a report page.
type reportData struct {
	TaskID     string
	State      string
	BadgeClass string
	Content    template.JS // JSON-encoded markdown string, safe for JS embedding.
	HasContent bool
	IsWorking  bool
}

// NewServer returns an HTTP handler that serves synthesizer reports as HTML pages.
// It expects the request path to contain an {id} segment matching a synthesizer task ID.
func NewServer(s *store.Store) http.Handler {
	tmpl := template.Must(template.New("report").Parse(pageTemplate))

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		id := r.PathValue("id")

		taskMeta, err := s.GetIndexed(ctx, a2a.TaskID(id))
		if errors.Is(err, a2a.ErrTaskNotFound) {
			log.Info(ctx, "report source does not exist")
			http.Error(w, "Report not found", http.StatusNotFound)
			return
		}
		if err != nil {
			log.Warn(ctx, "report source query failed", "cause", err)
			http.Error(w, "Service unavailable", http.StatusServiceUnavailable)
			return
		}
		if taskMeta.Agent != domain.AgentSynthesizer {
			log.Warn(ctx, "task is not a synthesizer report", "author", taskMeta.Agent)
			http.Error(w, "Report not found", http.StatusNotFound)
			return
		}

		task, err := s.Get(ctx, a2a.TaskID(id))
		if err != nil {
			log.Warn(ctx, "report source read failed", "cause", err)
			http.Error(w, "Service unavailable", http.StatusServiceUnavailable)
			return
		}

		markdown := extractMarkdown(task.Task)
		contentJSON, _ := json.Marshal(markdown)
		state := task.Task.Status.State
		data := reportData{
			TaskID:     id,
			State:      stateLabel(state),
			BadgeClass: badgeClass(state),
			Content:    template.JS(contentJSON),
			HasContent: markdown != "",
			IsWorking:  !state.Terminal(),
		}

		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		if data.IsWorking {
			w.Header().Set("Refresh", "5")
		}
		tmpl.Execute(w, data)
	})
}

// extractMarkdown collects all text parts from the task's artifacts.
func extractMarkdown(task *a2a.Task) string {
	var parts []string
	for _, artifact := range task.Artifacts {
		for _, part := range artifact.Parts {
			if text := part.Text(); text != "" {
				parts = append(parts, text)
			}
		}
	}
	return strings.Join(parts, "\n\n")
}

func stateLabel(s a2a.TaskState) string {
	switch s {
	case a2a.TaskStateCompleted:
		return "Completed"
	case a2a.TaskStateWorking:
		return "In Progress"
	case a2a.TaskStateFailed:
		return "Failed"
	case a2a.TaskStateCanceled:
		return "Canceled"
	case a2a.TaskStateSubmitted:
		return "Submitted"
	default:
		return string(s)
	}
}

func badgeClass(s a2a.TaskState) string {
	switch s {
	case a2a.TaskStateCompleted:
		return "badge-completed"
	case a2a.TaskStateWorking, a2a.TaskStateSubmitted:
		return "badge-working"
	case a2a.TaskStateFailed:
		return "badge-failed"
	default:
		return "badge-default"
	}
}

const pageTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Deep Research Report</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

body{
  font-family:Georgia,'Times New Roman',serif;
  background:#f6f7f9;
  color:#1d1d2e;
  line-height:1.8;
}

/* ── header ── */
.header{
  background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
  color:#fff;
  padding:2.5rem 2rem;
}
.header-inner{max-width:780px;margin:0 auto}
.header h1{
  font-size:1.5rem;font-weight:400;margin:0 0 .6rem;
  letter-spacing:.02em;
  font-family:'Helvetica Neue',Arial,sans-serif;
}
.meta{
  display:flex;align-items:center;gap:.75rem;
  font-size:.8rem;opacity:.85;
  font-family:'Helvetica Neue',Arial,sans-serif;
}
.badge{
  display:inline-block;padding:.15rem .55rem;border-radius:3px;
  font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;
}
.badge-completed{background:#27ae60;color:#fff}
.badge-working{background:#f39c12;color:#fff}
.badge-failed{background:#e74c3c;color:#fff}
.badge-default{background:#7f8c8d;color:#fff}

/* ── content area ── */
.content{max-width:780px;margin:0 auto;padding:2.5rem 2rem 4rem}

/* ── working spinner ── */
.working{text-align:center;padding:4rem 2rem;color:#7f8c8d}
.spinner{
  width:32px;height:32px;
  border:3px solid #dde;border-top-color:#0f3460;
  border-radius:50%;
  animation:spin .7s linear infinite;
  margin:0 auto 1.5rem;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── empty state ── */
.empty{text-align:center;padding:3rem 2rem;color:#999}

/* ── markdown body ── */
.report h1{
  font-size:1.7rem;font-weight:700;
  border-bottom:2px solid #e0e0e0;padding-bottom:.4rem;
  margin:2.5rem 0 1rem;color:#1a1a2e;
}
.report h1:first-child{margin-top:0}
.report h2{font-size:1.35rem;font-weight:600;margin:2rem 0 .75rem;color:#16213e}
.report h3{font-size:1.1rem;font-weight:600;margin:1.5rem 0 .5rem;color:#0f3460}
.report h4{font-size:1rem;font-weight:600;margin:1.25rem 0 .4rem;color:#333}
.report p{margin:0 0 1rem;text-align:justify}
.report a{color:#0f3460;text-decoration:none;border-bottom:1px solid #c0d0e0;transition:border-color .2s}
.report a:hover{border-bottom-color:#0f3460}
.report strong{font-weight:700}
.report ul,.report ol{margin:0 0 1rem;padding-left:1.5rem}
.report li{margin-bottom:.3rem}
.report li>ul,.report li>ol{margin-top:.3rem;margin-bottom:0}
.report blockquote{
  border-left:3px solid #0f3460;margin:1rem 0;padding:.5rem 1rem;
  background:#f0f4f8;color:#4a4a6a;font-style:italic;
}
.report code{
  font-family:'SF Mono','Fira Code',Consolas,monospace;
  font-size:.85em;background:#eef1f5;padding:.12em .3em;border-radius:3px;
}
.report pre{
  background:#1a1a2e;color:#e0e0e0;padding:1rem 1.25rem;
  border-radius:6px;overflow-x:auto;font-size:.85rem;line-height:1.5;margin:1rem 0;
}
.report pre code{background:none;padding:0;color:inherit;font-size:inherit}
.report table{width:100%;border-collapse:collapse;margin:1rem 0;font-size:.9rem}
.report th,.report td{padding:.55rem .75rem;border:1px solid #d0d0d0;text-align:left}
.report th{background:#f0f4f8;font-weight:600}
.report tr:nth-child(even){background:#fafbfc}
.report hr{border:none;border-top:1px solid #e0e0e0;margin:2rem 0}
.report img{max-width:100%;height:auto;border-radius:4px;margin:1rem 0}

/* ── print ── */
@media print{
  .header{background:#fff!important;color:#000;box-shadow:none;border-bottom:2px solid #000}
  .badge{border:1px solid #000}
  body{background:#fff}
  .content{padding:1rem 0}
}

/* ── mobile ── */
@media(max-width:640px){
  .content{padding:1.5rem 1rem}
  .header{padding:1.5rem 1rem}
  .report h1{font-size:1.35rem}
}
</style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <h1>Deep Research Report</h1>
    <div class="meta">
      <span class="badge {{.BadgeClass}}">{{.State}}</span>
      <span>{{.TaskID}}</span>
    </div>
  </div>
</div>

<div class="content">
{{if and .IsWorking (not .HasContent)}}
  <div class="working">
    <div class="spinner"></div>
    <p>This report is being generated. The page will refresh automatically.</p>
  </div>
{{else if not .HasContent}}
  <div class="empty"><p>No content available for this report.</p></div>
{{else}}
  {{if .IsWorking}}
  <div style="background:#fef9e7;border:1px solid #f9e79f;border-radius:4px;padding:.6rem 1rem;margin-bottom:1.5rem;font-size:.85rem;font-family:'Helvetica Neue',Arial,sans-serif;color:#7d6608">
    This report is still being generated and may be incomplete. The page will refresh automatically.
  </div>
  {{end}}
  <div class="report" id="report"></div>
{{end}}
</div>

{{if .HasContent}}
<script src="https://cdn.jsdelivr.net/npm/marked@15/marked.min.js"></script>
<script>
(function(){
  var raw = {{.Content}};
  marked.setOptions({gfm:true,breaks:false});
  document.getElementById('report').innerHTML = marked.parse(raw);
})();
</script>
{{end}}
</body>
</html>`
