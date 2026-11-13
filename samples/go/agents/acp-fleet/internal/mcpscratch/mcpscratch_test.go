package mcpscratch_test

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
	"testing"

	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/mcpscratch"
)

func TestRun(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	in, out := io.Pipe()
	resR, resW := io.Pipe()
	go func() {
		resW.CloseWithError(mcpscratch.Run(root, in, resW))
	}()
	enc := json.NewEncoder(out)
	dec := bufio.NewReader(resR)
	call := func(method string, params any) map[string]any {
		t.Helper()
		if err := enc.Encode(map[string]any{"jsonrpc": "2.0", "id": 1, "method": method, "params": params}); err != nil {
			t.Fatalf("Encode() error = %v", err)
		}
		line, err := dec.ReadBytes('\n')
		if err != nil {
			t.Fatalf("ReadBytes() error = %v", err)
		}
		var resp map[string]any
		if err := json.Unmarshal(line, &resp); err != nil {
			t.Fatalf("Unmarshal() error = %v", err)
		}
		return resp
	}
	text := func(resp map[string]any) string {
		content := resp["result"].(map[string]any)["content"].([]any)
		return content[0].(map[string]any)["text"].(string)
	}

	tests := []struct {
		name   string
		method string
		params any
		want   string
	}{
		{name: "write", method: "tools/call", params: map[string]any{"name": "write_file", "arguments": map[string]string{"path": "a.txt", "content": "hello"}}, want: "wrote a.txt"},
		{name: "read", method: "tools/call", params: map[string]any{"name": "read_file", "arguments": map[string]string{"path": "a.txt"}}, want: "hello"},
		{name: "list", method: "tools/call", params: map[string]any{"name": "list_files"}, want: "a.txt"},
		{name: "escape", method: "tools/call", params: map[string]any{"name": "read_file", "arguments": map[string]string{"path": "../etc/passwd"}}, want: "path escapes from parent"},
	}
	for _, tc := range tests {
		if got := text(call(tc.method, tc.params)); !strings.Contains(got, tc.want) {
			t.Fatalf("%s: tools/call = %q, want %q", tc.name, got, tc.want)
		}
	}
	if err := out.Close(); err != nil {
		t.Fatalf("Close() error = %v", err)
	}
}
