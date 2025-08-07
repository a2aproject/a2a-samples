package client

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"a2a/models"
)

func TestSendTask(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req models.JSONRPCRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatal(err)
		}

		if req.Method != "message/send" {
			t.Errorf("expected method message/send, got %s", req.Method)
		}

		task := &models.Task{
			ID: "123",
			Status: models.TaskStatus{
				State: models.TaskStateSubmitted,
			},
		}

		resp := models.JSONRPCResponse{
			JSONRPCMessage: models.JSONRPCMessage{
				JSONRPC: "2.0",
			},
			Result: task,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	client := NewClient(server.URL)
	params := models.TaskSendParams{
		ID: "123",
		Message: models.Message{
			Role: "user",
			Parts: []models.Part{
				{
					Text: stringPtr("test message"),
				},
			},
		},
	}

	resp, err := client.SendTask(params)
	if err != nil {
		t.Fatal(err)
	}

	task, ok := resp.Result.(*models.Task)
	if !ok {
		t.Fatal("expected result to be a Task")
	}

	if task.ID != "123" {
		t.Errorf("expected task ID 123, got %s", task.ID)
	}

	if task.Status.State != models.TaskStateSubmitted {
		t.Errorf("expected task status %s, got %s", models.TaskStateSubmitted, task.Status.State)
	}
}

func TestGetTask(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req models.JSONRPCRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatal(err)
		}

		if req.Method != "tasks/get" {
			t.Errorf("expected method tasks/get, got %s", req.Method)
		}

		task := &models.Task{
			ID: "123",
			Status: models.TaskStatus{
				State: models.TaskStateCompleted,
			},
		}

		resp := models.JSONRPCResponse{
			JSONRPCMessage: models.JSONRPCMessage{
				JSONRPC: "2.0",
			},
			Result: task,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	client := NewClient(server.URL)
	params := models.TaskQueryParams{
		TaskIDParams: models.TaskIDParams{
			ID: "123",
		},
	}

	resp, err := client.GetTask(params)
	if err != nil {
		t.Fatal(err)
	}

	task, ok := resp.Result.(*models.Task)
	if !ok {
		t.Fatal("expected result to be a Task")
	}

	if task.ID != "123" {
		t.Errorf("expected task ID 123, got %s", task.ID)
	}

	if task.Status.State != models.TaskStateCompleted {
		t.Errorf("expected task status %s, got %s", models.TaskStateCompleted, task.Status.State)
	}
}

func TestCancelTask(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req models.JSONRPCRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatal(err)
		}

		if req.Method != "tasks/cancel" {
			t.Errorf("expected method tasks/cancel, got %s", req.Method)
		}

		task := &models.Task{
			ID: "123",
			Status: models.TaskStatus{
				State: models.TaskStateCanceled,
			},
		}

		resp := models.JSONRPCResponse{
			JSONRPCMessage: models.JSONRPCMessage{
				JSONRPC: "2.0",
			},
			Result: task,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	client := NewClient(server.URL)
	params := models.TaskIDParams{
		ID: "123",
	}

	resp, err := client.CancelTask(params)
	if err != nil {
		t.Fatal(err)
	}

	task, ok := resp.Result.(*models.Task)
	if !ok {
		t.Fatal("expected result to be a Task")
	}

	if task.ID != "123" {
		t.Errorf("expected task ID 123, got %s", task.ID)
	}

	if task.Status.State != models.TaskStateCanceled {
		t.Errorf("expected task status %s, got %s", models.TaskStateCanceled, task.Status.State)
	}
}

func TestErrorResponse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		resp := models.JSONRPCResponse{
			JSONRPCMessage: models.JSONRPCMessage{
				JSONRPC: "2.0",
			},
			Error: &models.JSONRPCError{
				Code:    -32000,
				Message: "Task not found",
			},
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	client := NewClient(server.URL)
	params := models.TaskQueryParams{
		TaskIDParams: models.TaskIDParams{
			ID: "123",
		},
	}

	_, err := client.GetTask(params)
	if err == nil {
		t.Fatal("expected error, got nil")
	}

	expectedError := "A2A error: Task not found (code: -32000)"
	if err.Error() != expectedError {
		t.Errorf("expected error %q, got %q", expectedError, err.Error())
	}
}

func TestSendTaskStreaming(t *testing.T) {
	// Create a channel to signal when all events have been sent
	done := make(chan struct{})
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify request headers
		if r.Header.Get("Accept") != "text/event-stream" {
			t.Errorf("expected Accept header to be text/event-stream, got %s", r.Header.Get("Accept"))
		}

		// Verify the request body
		var req models.JSONRPCRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatal(err)
		}

		if req.Method != "message/send" {
			t.Errorf("expected method message/send, got %s", req.Method)
		}

		// Set response headers for streaming
		w.Header().Set("Content-Type", "application/json")
		w.(http.Flusher).Flush()

		// Send multiple events
		events := []*models.Task{
			{
				ID: "123",
				Status: models.TaskStatus{
					State: models.TaskStateWorking,
				},
			},
			{
				ID: "123",
				Status: models.TaskStatus{
					State: models.TaskStateCompleted,
				},
			},
		}

		for _, event := range events {
			resp := models.SendTaskStreamingResponse{
				JSONRPCResponse: models.JSONRPCResponse{
					JSONRPCMessage: models.JSONRPCMessage{
						JSONRPC: "2.0",
					},
				},
				Result: event,
			}

			if err := json.NewEncoder(w).Encode(resp); err != nil {
				t.Fatal(err)
			}
			w.(http.Flusher).Flush()
		}

		close(done)
	}))
	defer server.Close()

	client := NewClient(server.URL)
	params := models.TaskSendParams{
		ID: "123",
		Message: models.Message{
			Role: "user",
			Parts: []models.Part{
				{
					Text: stringPtr("test message"),
				},
			},
		},
	}

	eventChan := make(chan any)
	errChan := make(chan error, 1)

	// Start streaming
	go func() {
		errChan <- client.SendTaskStreaming(params, eventChan)
		close(eventChan)
	}()

	// Collect and verify events
	var events []models.Task
	for event := range eventChan {
		// The event should be a json.RawMessage that we need to unmarshal into a Task
		rawMsg, ok := event.(json.RawMessage)
		if !ok {
			t.Fatalf("expected event to be a json.RawMessage, but was %v with type %T", event, event)
		}
		var task models.Task
		if err := json.Unmarshal(rawMsg, &task); err != nil {
			t.Fatalf("failed to unmarshal task: %v", err)
		}
		events = append(events, task)
	}

	// Check for any errors from streaming
	if err := <-errChan; err != nil {
		t.Fatal(err)
	}

	// Wait for server to finish sending events
	<-done

	// Verify we received the expected number of events
	if len(events) != 2 {
		t.Errorf("expected 2 events, got %d", len(events))
	}

	// Verify the events...
	if events[0].Status.State != models.TaskStateWorking {
		t.Errorf("expected first event state to be %s, got %s", models.TaskStateWorking, events[0].Status.State)
	}

	if events[1].Status.State != models.TaskStateCompleted {
		t.Errorf("expected second event state to be %s, got %s", models.TaskStateCompleted, events[1].Status.State)
	}
}

func stringPtr(s string) *string {
	return &s
}
