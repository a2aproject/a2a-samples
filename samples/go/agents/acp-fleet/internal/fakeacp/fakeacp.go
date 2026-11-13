// Package fakeacp is a scripted ACP agent that speaks JSON-RPC over stdio, so
// that the fleet runs without model keys. The prompt text selects the behavior:
//
//	save <note>      asks permission, then appends the note to $HOME/notes.txt
//	scratch <text>   appends the text to scratch.txt in the session's working directory
//	work <seconds>   reports a step every second until done or canceled
//	fill <file> <KiB> writes random bytes to the file in the working directory
//	size <file>      reports the size and the SHA-256 of the file in the working directory
//	anything else    replies with the turn number and the earlier messages
//
// Sessions are kept in $HOME/sessions, so session/load works in a new process.
package fakeacp

import (
	"bufio"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Config configures the agent.
type Config struct {
	// Server is the name of the server running the agent, shown in replies.
	Server string
	// Home is the directory the agent keeps its sessions and notes in.
	Home string
}

type message struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type session struct {
	ID    string `json:"id"`
	Turns []turn `json:"turns"`

	cwd     string
	mcp     []string
	loaded  bool
	cancel  context.CancelFunc
	running bool
}

type turn struct {
	Server string `json:"server"`
	Text   string `json:"text"`
}

type agent struct {
	cfg Config

	writeMu sync.Mutex
	enc     *json.Encoder

	mu       sync.Mutex
	sessions map[string]*session
	nextID   int
	pending  map[string]chan message
	wg       sync.WaitGroup
}

// Run serves the ACP agent on in and out until in ends.
func Run(cfg Config, in io.Reader, out io.Writer) error {
	a := &agent{cfg: cfg, enc: json.NewEncoder(out), sessions: map[string]*session{}, pending: map[string]chan message{}}
	r := bufio.NewReader(in)
	for {
		line, err := r.ReadBytes('\n')
		if len(strings.TrimSpace(string(line))) > 0 {
			var m message
			if jsonErr := json.Unmarshal(line, &m); jsonErr != nil {
				return fmt.Errorf("decoding a message: %w", jsonErr)
			}
			a.dispatch(m)
		}
		if errors.Is(err, io.EOF) {
			a.cancelAll()
			a.wg.Wait()
			return nil
		}
		if err != nil {
			return err
		}
	}
}

func (a *agent) dispatch(m message) {
	switch {
	case m.Method == "" && m.ID != nil:
		a.mu.Lock()
		ch := a.pending[string(m.ID)]
		delete(a.pending, string(m.ID))
		a.mu.Unlock()
		if ch != nil {
			ch <- m
		}
	case m.Method == "session/cancel":
		var p struct {
			SessionID string `json:"sessionId"`
		}
		if err := json.Unmarshal(m.Params, &p); err == nil {
			a.cancel(p.SessionID)
		}
	case m.ID == nil:
	case m.Method == "session/prompt":
		a.wg.Add(1)
		go func() {
			defer a.wg.Done()
			a.respond(m.ID)(a.prompt(m.Params))
		}()
	default:
		a.respond(m.ID)(a.handle(m.Method, m.Params))
	}
}

func (a *agent) handle(method string, params json.RawMessage) (any, error) {
	switch method {
	case "initialize":
		return map[string]any{"protocolVersion": 1, "agentCapabilities": map[string]any{"loadSession": true}}, nil
	case "session/new", "session/load":
		var p struct {
			SessionID  string            `json:"sessionId"`
			Cwd        string            `json:"cwd"`
			MCPServers []json.RawMessage `json:"mcpServers"`
		}
		if err := json.Unmarshal(params, &p); err != nil {
			return nil, err
		}
		s := &session{ID: p.SessionID, cwd: p.Cwd, mcp: mcpNames(p.MCPServers)}
		if method == "session/load" {
			stored, err := a.load(p.SessionID)
			if err != nil {
				return nil, err
			}
			s.Turns, s.loaded = stored.Turns, true
		} else {
			a.mu.Lock()
			a.nextID++
			s.ID = fmt.Sprintf("sess-%d-%d", time.Now().UnixNano(), a.nextID)
			a.mu.Unlock()
			if err := a.store(s); err != nil {
				return nil, err
			}
		}
		a.mu.Lock()
		a.sessions[s.ID] = s
		a.mu.Unlock()
		if method == "session/load" {
			return map[string]any{}, nil
		}
		return map[string]any{"sessionId": s.ID}, nil
	}
	return nil, &rpcError{Code: -32601, Message: "method not found: " + method}
}

func (a *agent) prompt(params json.RawMessage) (any, error) {
	var p struct {
		SessionID string `json:"sessionId"`
		Prompt    []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"prompt"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, err
	}
	var parts []string
	for _, b := range p.Prompt {
		if b.Type == "text" {
			parts = append(parts, b.Text)
		}
	}
	text := strings.TrimSpace(strings.Join(parts, " "))

	a.mu.Lock()
	s := a.sessions[p.SessionID]
	if s == nil {
		a.mu.Unlock()
		return nil, fmt.Errorf("unknown session %q", p.SessionID)
	}
	ctx, cancel := context.WithCancel(context.Background())
	s.cancel, s.running = cancel, true
	a.mu.Unlock()
	defer func() {
		a.mu.Lock()
		s.running = false
		a.mu.Unlock()
		cancel()
	}()

	reply, err := a.run(ctx, s, text)
	if errors.Is(err, context.Canceled) {
		return map[string]any{"stopReason": "cancelled"}, nil
	}
	if err != nil {
		return nil, err
	}
	a.chunk(s.ID, reply)
	s.Turns = append(s.Turns, turn{Server: a.cfg.Server, Text: text})
	if err := a.store(s); err != nil {
		return nil, err
	}
	return map[string]any{"stopReason": "end_turn"}, nil
}

func (a *agent) run(ctx context.Context, s *session, text string) (string, error) {
	cmd, arg, _ := strings.Cut(text, " ")
	switch cmd {
	case "save":
		return a.save(ctx, s, arg)
	case "scratch":
		path := filepath.Join(s.cwd, "scratch.txt")
		if err := appendLine(path, arg); err != nil {
			return "", err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return "", err
		}
		return a.prefix(len(s.Turns)+1) + "scratch.txt: " + strings.Join(strings.Fields(string(data)), ", "), nil
	case "fill", "size":
		return a.file(s, cmd, arg)
	case "work":
		n, err := strconv.Atoi(arg)
		if err != nil || n <= 0 {
			n = 10
		}
		for i := 1; i <= n; i++ {
			select {
			case <-ctx.Done():
				return "", ctx.Err()
			case <-time.After(time.Second):
			}
			a.chunk(s.ID, fmt.Sprintf("%s: step %d/%d\n", a.cfg.Server, i, n))
		}
		return a.prefix(len(s.Turns)+1) + "done", nil
	}
	return a.describe(s, text), nil
}

func (a *agent) save(ctx context.Context, s *session, note string) (string, error) {
	toolID := fmt.Sprintf("save-%d", len(s.Turns)+1)
	title := fmt.Sprintf("Append %q to notes.txt", note)
	a.update(s.ID, map[string]any{"sessionUpdate": "tool_call", "toolCallId": toolID, "title": title, "kind": "edit", "status": "pending", "rawInput": map[string]any{"path": "notes.txt", "text": note}})
	resp, err := a.request(ctx, "session/request_permission", map[string]any{
		"sessionId": s.ID,
		"toolCall":  map[string]any{"toolCallId": toolID, "title": title, "kind": "edit"},
		"options": []map[string]any{
			{"optionId": "allow", "name": "Allow once", "kind": "allow_once"},
			{"optionId": "reject", "name": "Reject", "kind": "reject_once"},
		},
	})
	if err != nil {
		return "", err
	}
	var out struct {
		Outcome struct {
			Outcome  string `json:"outcome"`
			OptionID string `json:"optionId"`
		} `json:"outcome"`
	}
	if err := json.Unmarshal(resp, &out); err != nil {
		return "", err
	}
	if out.Outcome.Outcome == "cancelled" {
		return "", context.Canceled
	}
	if out.Outcome.OptionID != "allow" {
		a.update(s.ID, map[string]any{"sessionUpdate": "tool_call_update", "toolCallId": toolID, "status": "failed"})
		return a.prefix(len(s.Turns)+1) + "not saved", nil
	}
	path := filepath.Join(a.cfg.Home, "notes.txt")
	if err := appendLine(path, note); err != nil {
		return "", err
	}
	a.update(s.ID, map[string]any{"sessionUpdate": "tool_call_update", "toolCallId": toolID, "status": "completed"})
	return a.prefix(len(s.Turns)+1) + "saved. " + a.notes(), nil
}

func (a *agent) describe(s *session, text string) string {
	var sb strings.Builder
	sb.WriteString(a.prefix(len(s.Turns) + 1))
	switch {
	case len(s.Turns) == 0:
		sb.WriteString("new session")
	case s.loaded:
		sb.WriteString("session loaded; " + where(s.Turns))
	default:
		sb.WriteString("same process")
	}
	if len(s.Turns) > 0 {
		var earlier []string
		for _, t := range s.Turns {
			earlier = append(earlier, t.Text)
		}
		fmt.Fprintf(&sb, ". Earlier you said: %s", strings.Join(earlier, " | "))
	} else {
		fmt.Fprintf(&sb, ". You said: %s", text)
	}
	if notes := a.notes(); notes != "" {
		sb.WriteString(". " + notes)
	}
	if len(s.mcp) > 0 {
		sb.WriteString(". MCP: " + strings.Join(s.mcp, ", "))
	}
	if err := os.Remove(filepath.Join(s.cwd, "SCRATCH_LOST.txt")); err == nil {
		sb.WriteString(". Scratch was lost when the conversation moved")
	}
	return sb.String()
}

func (a *agent) file(s *session, cmd, arg string) (string, error) {
	name, kib, _ := strings.Cut(arg, " ")
	path := filepath.Join(s.cwd, filepath.Base(name))
	if cmd == "fill" {
		n, err := strconv.Atoi(kib)
		if err != nil {
			return "", fmt.Errorf("fill %s: %w", arg, err)
		}
		data := make([]byte, n<<10)
		if _, err := rand.Read(data); err != nil {
			return "", err
		}
		if err := os.WriteFile(path, data, 0o600); err != nil {
			return "", err
		}
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(data)
	return fmt.Sprintf("%s%s: %d bytes, sha256 %x", a.prefix(len(s.Turns)+1), filepath.Base(name), len(data), sum[:4]), nil
}

func (a *agent) prefix(n int) string { return fmt.Sprintf("%s: turn %d, ", a.cfg.Server, n) }

func (a *agent) notes() string {
	data, err := os.ReadFile(filepath.Join(a.cfg.Home, "notes.txt"))
	if err != nil || len(data) == 0 {
		return ""
	}
	return "Notes: " + strings.Join(strings.Split(strings.TrimSpace(string(data)), "\n"), ", ")
}

// where summarizes which servers ran the turns, for example "turns 1-3 ran on server-2, 4 on server-1".
func where(turns []turn) string {
	var parts []string
	for i := 0; i < len(turns); {
		j := i
		for j+1 < len(turns) && turns[j+1].Server == turns[i].Server {
			j++
		}
		span := strconv.Itoa(i + 1)
		if j > i {
			span += "-" + strconv.Itoa(j+1)
		}
		if len(parts) == 0 {
			parts = append(parts, fmt.Sprintf("turns %s ran on %s", span, turns[i].Server))
		} else {
			parts = append(parts, fmt.Sprintf("%s on %s", span, turns[i].Server))
		}
		i = j + 1
	}
	return strings.Join(parts, ", ")
}

func mcpNames(servers []json.RawMessage) []string {
	var names []string
	for _, raw := range servers {
		var s struct {
			Name string `json:"name"`
		}
		if json.Unmarshal(raw, &s) == nil && s.Name != "" {
			names = append(names, s.Name)
		}
	}
	return names
}

func (a *agent) cancel(sessionID string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if s := a.sessions[sessionID]; s != nil && s.running {
		s.cancel()
	}
}

func (a *agent) cancelAll() {
	a.mu.Lock()
	defer a.mu.Unlock()
	for _, s := range a.sessions {
		if s.running {
			s.cancel()
		}
	}
	for id, ch := range a.pending {
		close(ch)
		delete(a.pending, id)
	}
}

func (a *agent) sessionPath(id string) string {
	return filepath.Join(a.cfg.Home, "sessions", filepath.Base(id)+".json")
}

func (a *agent) load(id string) (*session, error) {
	data, err := os.ReadFile(a.sessionPath(id))
	if err != nil {
		return nil, fmt.Errorf("loading session %s: %w", id, err)
	}
	var s session
	if err := json.Unmarshal(data, &s); err != nil {
		return nil, err
	}
	return &s, nil
}

func (a *agent) store(s *session) error {
	path := a.sessionPath(s.ID)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	data, err := json.Marshal(s)
	if err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func appendLine(path, line string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	_, err = fmt.Fprintln(f, line)
	return errors.Join(err, f.Close())
}

func (a *agent) chunk(sessionID, text string) {
	a.update(sessionID, map[string]any{"sessionUpdate": "agent_message_chunk", "content": map[string]any{"type": "text", "text": text}})
}

func (a *agent) update(sessionID string, update map[string]any) {
	a.notify("session/update", map[string]any{"sessionId": sessionID, "update": update})
}

func (a *agent) notify(method string, params any) {
	raw, err := json.Marshal(params)
	if err == nil {
		a.write(message{JSONRPC: "2.0", Method: method, Params: raw})
	}
}

func (a *agent) request(ctx context.Context, method string, params any) (json.RawMessage, error) {
	raw, err := json.Marshal(params)
	if err != nil {
		return nil, err
	}
	a.mu.Lock()
	a.nextID++
	id := json.RawMessage(strconv.Quote("agent-" + strconv.Itoa(a.nextID)))
	ch := make(chan message, 1)
	a.pending[string(id)] = ch
	a.mu.Unlock()
	a.write(message{JSONRPC: "2.0", ID: id, Method: method, Params: raw})
	select {
	case m, ok := <-ch:
		if !ok {
			return nil, context.Canceled
		}
		if m.Error != nil {
			return nil, m.Error
		}
		return m.Result, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

func (a *agent) respond(id json.RawMessage) func(any, error) {
	return func(result any, err error) {
		m := message{JSONRPC: "2.0", ID: id}
		if err != nil {
			var rpcErr *rpcError
			if !errors.As(err, &rpcErr) {
				rpcErr = &rpcError{Code: -32603, Message: err.Error()}
			}
			m.Error = rpcErr
		} else {
			raw, marshalErr := json.Marshal(result)
			if marshalErr != nil {
				m.Error = &rpcError{Code: -32603, Message: marshalErr.Error()}
			}
			m.Result = raw
		}
		a.write(m)
	}
}

func (a *agent) write(m message) {
	a.writeMu.Lock()
	defer a.writeMu.Unlock()
	if err := a.enc.Encode(m); err != nil {
		fmt.Fprintf(os.Stderr, "fakeacp: writing a message: %v\n", err)
	}
}

func (e *rpcError) Error() string { return e.Message }
