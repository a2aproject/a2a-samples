// Package mcpscratch is a small MCP server over stdio that gives an agent file
// tools in its scratch directory: list_files, read_file and write_file. Paths
// can't leave the directory.
package mcpscratch

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"strings"
)

const maxFileSize = 1 << 20

type request struct {
	ID     json.RawMessage `json:"id,omitempty"`
	Method string          `json:"method"`
	Params json.RawMessage `json:"params,omitempty"`
}

type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

var tools = []map[string]any{
	{
		"name":        "list_files",
		"description": "Lists the files in the scratch directory.",
		"inputSchema": map[string]any{"type": "object", "properties": map[string]any{}},
	},
	{
		"name":        "read_file",
		"description": "Reads a file in the scratch directory.",
		"inputSchema": map[string]any{
			"type":       "object",
			"properties": map[string]any{"path": map[string]any{"type": "string"}},
			"required":   []string{"path"},
		},
	},
	{
		"name":        "write_file",
		"description": "Writes a file in the scratch directory, replacing its content.",
		"inputSchema": map[string]any{
			"type": "object",
			"properties": map[string]any{
				"path":    map[string]any{"type": "string"},
				"content": map[string]any{"type": "string"},
			},
			"required": []string{"path", "content"},
		},
	},
}

// Run serves the MCP server for the directory root on in and out until in ends.
func Run(root string, in io.Reader, out io.Writer) error {
	if err := os.MkdirAll(root, 0o700); err != nil {
		return err
	}
	dir, err := os.OpenRoot(root)
	if err != nil {
		return err
	}
	defer func() {
		if err := dir.Close(); err != nil {
			fmt.Fprintf(os.Stderr, "mcpscratch: closing %s: %v\n", root, err)
		}
	}()
	enc := json.NewEncoder(out)
	r := bufio.NewReader(in)
	for {
		line, readErr := r.ReadBytes('\n')
		if strings.TrimSpace(string(line)) != "" {
			var req request
			if err := json.Unmarshal(line, &req); err != nil {
				return fmt.Errorf("decoding a request: %w", err)
			}
			if req.ID != nil {
				result, err := handle(dir, req)
				resp := response{JSONRPC: "2.0", ID: req.ID, Result: result}
				if err != nil {
					resp.Result, resp.Error = nil, &rpcError{Code: -32601, Message: err.Error()}
				}
				if err := enc.Encode(resp); err != nil {
					return err
				}
			}
		}
		if errors.Is(readErr, io.EOF) {
			return nil
		}
		if readErr != nil {
			return readErr
		}
	}
}

func handle(dir *os.Root, req request) (any, error) {
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, err
		}
		return map[string]any{
			"protocolVersion": p.ProtocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "scratch", "version": "1.0.0"},
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": tools}, nil
	case "tools/call":
		var p struct {
			Name      string            `json:"name"`
			Arguments map[string]string `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, err
		}
		text, err := call(dir, p.Name, p.Arguments)
		if err != nil {
			return map[string]any{"content": []map[string]any{{"type": "text", "text": err.Error()}}, "isError": true}, nil
		}
		return map[string]any{"content": []map[string]any{{"type": "text", "text": text}}}, nil
	}
	return nil, fmt.Errorf("method not found: %s", req.Method)
}

func call(dir *os.Root, name string, args map[string]string) (string, error) {
	switch name {
	case "list_files":
		var files []string
		err := fs.WalkDir(dir.FS(), ".", func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if !d.IsDir() {
				files = append(files, path)
			}
			return nil
		})
		return strings.Join(files, "\n"), err
	case "read_file":
		f, err := dir.Open(args["path"])
		if err != nil {
			return "", err
		}
		data, err := io.ReadAll(io.LimitReader(f, maxFileSize+1))
		if err = errors.Join(err, f.Close()); err != nil {
			return "", err
		}
		if len(data) > maxFileSize {
			return "", fmt.Errorf("%s is larger than %d bytes", args["path"], maxFileSize)
		}
		return string(data), nil
	case "write_file":
		if len(args["content"]) > maxFileSize {
			return "", fmt.Errorf("content is larger than %d bytes", maxFileSize)
		}
		if err := dir.WriteFile(args["path"], []byte(args["content"]), 0o600); err != nil {
			return "", err
		}
		return "wrote " + args["path"], nil
	}
	return "", fmt.Errorf("unknown tool %q", name)
}
