package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"itk/agents/go/v03/pb"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2aclient"
	"github.com/a2aproject/a2a-go/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/a2asrv"
	"github.com/a2aproject/a2a-go/a2asrv/eventqueue"
	"github.com/a2aproject/a2a-go/a2asrv/push"
	"github.com/a2aproject/a2a-go/log"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/proto"

	"github.com/a2aproject/a2a-go/a2agrpc"
	"golang.org/x/sync/errgroup"
)

func shouldHold(inst *pb.Instruction) bool {
	if inst.GetReturnResponse() != nil && inst.GetReturnResponse().HoldTask {
		return true
	}
	if inst.GetSteps() != nil {
		for _, step := range inst.GetSteps().Instructions {
			if shouldHold(step) {
				return true
			}
		}
	}
	return false
}

type V03AgentExecutor struct {
	cancels sync.Map
}

func (e *V03AgentExecutor) Execute(ctx context.Context, reqCtx *a2asrv.RequestContext, queue eventqueue.Queue) error {
	log.Info(ctx, "Executing task", "taskId", reqCtx.Message.ID)

	ctx, cancel := context.WithCancel(ctx)
	e.cancels.Store(reqCtx.TaskID, cancel)
	defer e.cancels.Delete(reqCtx.TaskID)
	defer cancel()

	if reqCtx.StoredTask == nil {
		if err := queue.Write(ctx, a2a.NewSubmittedTask(reqCtx, reqCtx.Message)); err != nil {
			return err
		}
	}

	if err := queue.Write(ctx, a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateWorking, nil)); err != nil {
		return err
	}

	// 1. Extract Instruction from message parts
	var instruction pb.Instruction
	found := false
	for _, part := range reqCtx.Message.Parts {
		if filePart, ok := part.(a2a.FilePart); ok {
			if fileBytes, ok := filePart.File.(a2a.FileBytes); ok {
				rawBytes, err := base64.StdEncoding.DecodeString(fileBytes.Bytes)
				if err != nil {
					log.Error(ctx, "Failed to decode base64 bytes", err)
					continue
				}
				if err := proto.Unmarshal(rawBytes, &instruction); err == nil {
					found = true
					break
				}
			}
		}
	}

	if !found {
		errMsg := "Error: No valid Instruction found in request."
		log.Log(ctx, slog.LevelError, errMsg)
		if err := queue.Write(ctx, a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateFailed, nil)); err != nil {
			log.Error(ctx, "Failed to write status update", err)
		}
		return queue.Write(ctx, a2a.NewMessageForTask(a2a.MessageRoleAgent, reqCtx, a2a.TextPart{Text: errMsg}))
	}

	// 2. Handle Instruction
	results, err := e.handleInstruction(ctx, reqCtx, &instruction)
	log.Info(ctx, "handleInstruction results", "results", results)
	if err != nil {
		log.Error(ctx, "Error handling instruction", err)
		if err := queue.Write(ctx, a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateFailed, nil)); err != nil {
			log.Error(ctx, "Failed to write status update", err)
		}
		return err
	}

	// 3. Return response
	response := strings.Join(results, "\n")
	
	if shouldHold(&instruction) {
		log.Info(ctx, "Holding task as requested", "taskId", reqCtx.Message.ID)
		
		// First emitted event: the actual response
		// Emitted event: response + task-finished
		log.Info(ctx, "Emitting response and task-finished", "taskId", reqCtx.Message.ID)
		finnishedMsg := a2a.NewMessageForTask(a2a.MessageRoleAgent, reqCtx, a2a.TextPart{Text: response + "\ntask-finished"})
		
		if err := queue.Write(ctx, a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateWorking, finnishedMsg)); err != nil {
			return err
		}
		
		// Continue emitting periodic updates
		ticker := time.NewTicker(2 * time.Second)
		defer ticker.Stop()

		for i := 0; i < 5; i++ {
			select {
			case <-ctx.Done():
				log.Info(ctx, "Task cancelled, exiting hold loop", "taskId", reqCtx.Message.ID)
				event := a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateCanceled, nil)
				event.Final = true
				queue.Write(context.Background(), event)
				return nil
			case <-ticker.C:
				log.Info(ctx, "Emitting periodic status update with response", "taskId", reqCtx.Message.ID)
				bgCtx, cancelWrite := context.WithTimeout(context.Background(), 1*time.Second)
				err := queue.Write(bgCtx, a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateWorking, finnishedMsg))
				cancelWrite()
				if err != nil {
					log.Error(ctx, "Failed to write periodic update to queue", err)
				}
			}
		}
		log.Info(ctx, "Held task timed out, auto-completing", "taskId", reqCtx.Message.ID)
		event := a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateFailed, nil)
		event.Final = true
		queue.Write(context.Background(), event)
		return nil
	} else {
		msg := a2a.NewMessageForTask(a2a.MessageRoleAgent, reqCtx, a2a.TextPart{Text: response})
		event := a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateCompleted, msg)
		event.Final = true
		return queue.Write(ctx, event)
	}
}

func (e *V03AgentExecutor) handleInstruction(ctx context.Context, reqCtx *a2asrv.RequestContext, inst *pb.Instruction) ([]string, error) {
	switch {
	case inst.GetCallAgent() != nil:
		call := inst.GetCallAgent()
		log.Info(ctx, "Calling agent", "agentCardUri", call.AgentCardUri, "transport", call.Transport)

		// Resolve card and create client
		card, err := agentcard.DefaultResolver.Resolve(ctx, call.AgentCardUri)
		if err != nil {
			return nil, fmt.Errorf("failed to resolve agent card for %s: %w", call.AgentCardUri, err)
		}

		opts := []a2aclient.FactoryOption{
			a2aclient.WithGRPCTransport(grpc.WithTransportCredentials(insecure.NewCredentials())),
		}

		if call.GetPushNotification() != nil {
			url := call.GetPushNotification().GetUrl()
			if url == "" {
				return nil, fmt.Errorf("URL not specified in push_notification behavior")
			}
			opts = append(opts, a2aclient.WithConfig(a2aclient.Config{
				PushConfig: &a2a.PushConfig{
					URL:   fmt.Sprintf("%s/notifications", url),
					Token: "itk-token",
				},
			}))
		}

		tp := mapTransport(call.Transport)
		log.Info(ctx, "Mapped transport", "transport", tp)

		matchedInterfaces := selectInterfaces(tp, card)
		if len(matchedInterfaces) == 0 {
			return nil, fmt.Errorf("transport protocol %s is not supported by agent %s", tp, call.AgentCardUri)
		}

		// 3. Create a client with transport enforcement
		client, err := a2aclient.NewFromEndpoints(ctx, matchedInterfaces, opts...)
		if err != nil {
			return nil, fmt.Errorf("failed to connect to agent %s: %w", call.AgentCardUri, err)
		}

		// Wrap instruction back to a message
		wrappedMsg, err := wrapInstructionToRequest(call.Instruction)
		if err != nil {
			return nil, fmt.Errorf("failed to wrap nested instruction: %w", err)
		}

		var responses []string
		if call.GetResubscribe() != nil {
			if !call.Streaming {
				return nil, fmt.Errorf("re-subscription requires streaming to be enabled")
			}
			responses, err = e.handleCallAgentWithResubscribe(ctx, client, wrappedMsg)
			if err != nil {
				return nil, err
			}
		} else if call.Streaming {
			events := client.SendStreamingMessage(ctx, wrappedMsg)
			for ev, err := range events {
				if err != nil {
					return nil, fmt.Errorf("streaming call failed to agent %s: %w", call.AgentCardUri, err)
				}
				switch r := ev.(type) {
				case *a2a.TaskStatusUpdateEvent:
					if r.Status.Message != nil {
						for _, part := range r.Status.Message.Parts {
							if textPart, ok := part.(a2a.TextPart); ok {
								responses = append(responses, textPart.Text)
							}
						}
					}
				}
			}
		} else {
			result, err := client.SendMessage(ctx, wrappedMsg)
			if err != nil {
				return nil, fmt.Errorf("failed to send message to agent %s: %w", call.AgentCardUri, err)
			}
			switch r := result.(type) {
			case *a2a.Message:
				for _, part := range r.Parts {
					if textPart, ok := part.(a2a.TextPart); ok {
						responses = append(responses, textPart.Text)
					}
				}
			case *a2a.Task:
				if r.Status.Message != nil {
					for _, part := range r.Status.Message.Parts {
						if textPart, ok := part.(a2a.TextPart); ok {
							responses = append(responses, textPart.Text)
						}
					}
				}
				for _, msg := range r.History {
					if msg.Role == a2a.MessageRoleAgent {
						for _, part := range msg.Parts {
							if textPart, ok := part.(a2a.TextPart); ok {
								responses = append(responses, textPart.Text)
							}
						}
					}
				}
			default:
				return nil, fmt.Errorf("unexpected result type from SendMessage: %T", result)
			}
		}

		return responses, nil

	case inst.GetReturnResponse() != nil:
		return []string{inst.GetReturnResponse().Response}, nil

	case inst.GetSteps() != nil:
		var allResults []string
		for _, step := range inst.GetSteps().Instructions {
			results, err := e.handleInstruction(ctx, reqCtx, step)
			if err != nil {
				return nil, err
			}
			allResults = append(allResults, results...)
		}
		return allResults, nil

	default:
		return nil, fmt.Errorf("unknown instruction type")
	}
}

func (e *V03AgentExecutor) handleCallAgentWithResubscribe(ctx context.Context, client *a2aclient.Client, req *a2a.MessageSendParams) ([]string, error) {
	var responses []string
	log.Info(ctx, "Executing re-subscribe behavior")

	events := client.SendStreamingMessage(ctx, req)
	var taskID a2a.TaskID
	foundTask := false

	for ev, err := range events {
		if err != nil {
			return nil, fmt.Errorf("streaming call failed before disconnect: %w", err)
		}
		log.Info(ctx, "Event before disconnect", "event", ev)

		switch r := ev.(type) {
		case *a2a.Task:
			taskID = r.ID
			foundTask = true
		case *a2a.TaskStatusUpdateEvent:
			taskID = r.TaskID
			foundTask = true
		}

		if foundTask && taskID != "" {
			break // Disconnect!
		}
	}

	log.Info(ctx, "Disconnected from task. Now re-subscribing.", "taskID", taskID)

	resubEvents := client.ResubscribeToTask(ctx, &a2a.TaskIDParams{ID: taskID})

	var taskObj *a2a.Task
	for ev, err := range resubEvents {
		if err != nil {
			return nil, fmt.Errorf("re-subscribe failed: %w", err)
		}
		log.Info(ctx, "Event after re-subscribe", "event", ev)

		switch r := ev.(type) {
		case *a2a.Task:
			taskObj = r
			if r.Status.Message != nil {
				for _, part := range r.Status.Message.Parts {
					if textPart, ok := part.(a2a.TextPart); ok {
						t := textPart.Text
						t = strings.ReplaceAll(t, "task-finished", "")
						responses = append(responses, t)
						if strings.Contains(textPart.Text, "task-finished") {
							log.Info(ctx, "Found task-finished in Status.Message during loop, breaking.")
							goto EndLoop
						}
					}
				}
			}
			for _, msg := range r.History {
				if msg.Role == a2a.MessageRoleAgent {
					for _, part := range msg.Parts {
						if textPart, ok := part.(a2a.TextPart); ok {
							t := textPart.Text
							t = strings.ReplaceAll(t, "task-finished", "")
							responses = append(responses, t)
							if strings.Contains(textPart.Text, "task-finished") {
								log.Info(ctx, "Found task-finished in history during loop, breaking.")
								goto EndLoop
							}
						}
					}
				}
			}
		case *a2a.TaskStatusUpdateEvent:
			if r.Status.Message != nil {
				for _, part := range r.Status.Message.Parts {
					if textPart, ok := part.(a2a.TextPart); ok {
						t := textPart.Text
						t = strings.ReplaceAll(t, "task-finished", "")
						responses = append(responses, t)
						
						if strings.Contains(textPart.Text, "task-finished") {
                            log.Info(ctx, "Received task-finished after re-subscribe, breaking loop.")
							goto EndLoop
						}
					}
				}
			}
		}
	}
EndLoop:

	if len(responses) == 0 && taskObj != nil {
		log.Info(ctx, "Responses empty after loop, reading from history.")
		for _, msg := range taskObj.History {
			if msg.Role == a2a.MessageRoleAgent {
				for _, part := range msg.Parts {
					if textPart, ok := part.(a2a.TextPart); ok {
						t := textPart.Text
						t = strings.ReplaceAll(t, "task-finished", "")
						responses = append(responses, t)
					}
				}
			}
		}
	}

	log.Info(ctx, "Canceling task after retrieval.", "taskID", taskID)
	_, err := client.CancelTask(ctx, &a2a.TaskIDParams{ID: taskID})
	if err != nil {
		log.Error(ctx, "Failed to cancel task", err, "taskID", taskID)
		return responses, err
	}

	return responses, nil
}

func boolPtr(b bool) *bool {
	return &b
}

func (e *V03AgentExecutor) Cancel(ctx context.Context, reqCtx *a2asrv.RequestContext, queue eventqueue.Queue) error {
	log.Info(ctx, "Cancel requested", "taskId", reqCtx.TaskID)
	
	// Run in background to avoid blocking if queue is full
	go func() {
		bgCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		err := queue.Write(bgCtx, a2a.NewStatusUpdateEvent(reqCtx, a2a.TaskStateCanceled, nil))
		if err != nil {
			slog.Error("Failed to write cancel status to queue", "error", err)
		}
	}()

	if cancel, ok := e.cancels.Load(reqCtx.TaskID); ok {
		cancel.(context.CancelFunc)()
	}
	return nil
}

func wrapInstructionToRequest(inst *pb.Instruction) (*a2a.MessageSendParams, error) {
	instBytes, err := proto.Marshal(inst)
	if err != nil {
		return nil, err
	}
	b64Inst := base64.StdEncoding.EncodeToString(instBytes)

	msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.FilePart{
		File: a2a.FileBytes{
			Bytes: b64Inst,
			FileMeta: a2a.FileMeta{
				MimeType: "application/x-protobuf",
				Name:     "instruction.bin",
			},
		},
	})

	return &a2a.MessageSendParams{
		Config: &a2a.MessageSendConfig{
			Blocking: boolPtr(true),
		},
		Message: msg,
	}, nil
}

func mapTransport(t string) a2a.TransportProtocol {
	switch strings.ToUpper(t) {
	case "GRPC":
		return a2a.TransportProtocolGRPC
	case "HTTP_JSON":
		return a2a.TransportProtocolHTTPJSON
	default:
		return a2a.TransportProtocolJSONRPC
	}
}

func selectInterfaces(tp a2a.TransportProtocol, card *a2a.AgentCard) []a2a.AgentInterface {
	var matched []a2a.AgentInterface
	prefTp := card.PreferredTransport
	if prefTp == "" {
		prefTp = a2a.TransportProtocolJSONRPC
	}
	if prefTp == tp {
		matched = append(matched, a2a.AgentInterface{
			URL:       strings.TrimSuffix(card.URL, "/"),
			Transport: tp,
		})
	}

	for _, iface := range card.AdditionalInterfaces {
		if iface.Transport == tp {
			iface.URL = strings.TrimSuffix(iface.URL, "/")
			matched = append(matched, iface)
		}
	}
	return matched
}

type CustomLoggingInterceptor struct{}

func (CustomLoggingInterceptor) Before(ctx context.Context, callCtx *a2asrv.CallContext, req *a2asrv.Request) (context.Context, error) {
	payloadJSON, err := json.Marshal(req.Payload)
	if err != nil {
		payloadJSON = []byte(fmt.Sprintf("%+v", req.Payload))
	}
	log.Info(ctx, "A2A Call Started", "method", callCtx.Method(), "payload", string(payloadJSON))
	return ctx, nil
}

func (CustomLoggingInterceptor) After(ctx context.Context, callCtx *a2asrv.CallContext, resp *a2asrv.Response) error {
	payloadJSON, err := json.Marshal(resp.Payload)
	if err != nil {
		payloadJSON = []byte(fmt.Sprintf("%+v", resp.Payload))
	}
	log.Info(ctx, "A2A Call Finished", "method", callCtx.Method(), "response", string(payloadJSON), "error", resp.Err)
	return nil
}

var httpPort = flag.Int("httpPort", 10101, "HTTP port")
var grpcPort = flag.Int("grpcPort", 11001, "gRPC port")

func main() {
	if err := run(); err != nil {
		slog.Error("Server session ended with error", "error", err)
		os.Exit(1)
	}
}

func run() error {
	flag.Parse()

	logLevelStr := os.Getenv("ITK_LOG_LEVEL")
	if logLevelStr == "" {
		logLevelStr = "INFO"
	}
	var level slog.Level
	switch strings.ToUpper(logLevelStr) {
	case "DEBUG":
		level = slog.LevelDebug
	case "INFO":
		level = slog.LevelInfo
	case "WARN":
		level = slog.LevelWarn
	case "ERROR":
		level = slog.LevelError
	default:
		level = slog.LevelInfo
	}
	
	logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: level}))
	slog.SetDefault(logger)

	host := "127.0.0.1"
	jsonRPCAddr := fmt.Sprintf("http://127.0.0.1:%d/jsonrpc", *httpPort)
	grpcAddr := fmt.Sprintf("127.0.0.1:%d", *grpcPort)

	skill := a2a.AgentSkill{
		ID:          "itk_v03_proto_skill",
		Name:        "ITK v03 Proto Skill",
		Description: "Handles raw byte Instruction protos in v03 subproject.",
		Tags:        []string{"proto", "v03", "itk"},
		Examples:    []string{"Roll a dice", "Call another agent"},
	}

	agentCard := &a2a.AgentCard{
		Name:               "ITK v03 Agent",
		Description:        "Multi-transport agent supporting raw Instruction protos.",
		URL:                jsonRPCAddr,
		Version:            "0.3.0",
		DefaultInputModes:  []string{"text"},
		DefaultOutputModes: []string{"text"},
		Capabilities:       a2a.AgentCapabilities{Streaming: true},
		Skills:             []a2a.AgentSkill{skill},
		PreferredTransport: a2a.TransportProtocolJSONRPC,
		AdditionalInterfaces: []a2a.AgentInterface{
			{URL: jsonRPCAddr, Transport: a2a.TransportProtocolJSONRPC},
			{URL: grpcAddr, Transport: a2a.TransportProtocolGRPC},
		},
		ProtocolVersion: "0.3.0",
	}

	pushStore := push.NewInMemoryStore()
	pushSender := push.NewHTTPPushSender(nil)

	executor := &V03AgentExecutor{}
	requestHandler := a2asrv.NewHandler(
		executor,
		a2asrv.WithExtendedAgentCard(agentCard),
		a2asrv.WithCallInterceptor(CustomLoggingInterceptor{}),
		a2asrv.WithPushNotifications(pushStore, pushSender),
	)

	jsonrpcHandler := a2asrv.NewJSONRPCHandler(requestHandler)
	cardHandler := a2asrv.NewStaticAgentCardHandler(agentCard)

	mux := http.NewServeMux()
	mux.Handle(fmt.Sprintf("/jsonrpc%s", a2asrv.WellKnownAgentCardPath), cardHandler)
	mux.Handle("/jsonrpc", jsonrpcHandler)

	httpServer := &http.Server{
		Addr:              host + ":" + fmt.Sprintf("%d", *httpPort),
		Handler:           loggingMiddleware(logger, mux),
		ReadHeaderTimeout: 3 * time.Second,
	}

	grpcServer := grpc.NewServer(
		grpc.UnaryInterceptor(unaryLoggingInterceptor(logger)),
		grpc.StreamInterceptor(streamLoggingInterceptor(logger)),
	)
	grpcHandler := a2agrpc.NewHandler(requestHandler)
	grpcHandler.RegisterWith(grpcServer)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	ctx = log.WithLogger(ctx, logger)

	g, ctx := errgroup.WithContext(ctx)

	g.Go(func() error {
		log.Info(ctx, "Starting HTTP server", "address", fmt.Sprintf("%s:%d", host, *httpPort))
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			return fmt.Errorf("HTTP server failed: %w", err)
		}
		return nil
	})

	g.Go(func() error {
		lis, err := net.Listen("tcp", host+":"+fmt.Sprintf("%d", *grpcPort))
		if err != nil {
			return err
		}
		log.Info(ctx, "Starting gRPC server", "address", fmt.Sprintf("%s:%d", host, *grpcPort))
		if err := grpcServer.Serve(lis); err != nil {
			return fmt.Errorf("gRPC server failed: %w", err)
		}
		return nil
	})

	g.Go(func() error {
		<-ctx.Done()
		log.Info(ctx, "Shutting down servers")

		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err := httpServer.Shutdown(shutdownCtx); err != nil {
			log.Error(ctx, "HTTP server shutdown error", err)
		}

		grpcServer.GracefulStop()
		log.Info(ctx, "Servers closed")
		return nil
	})

	return g.Wait()
}

func loggingMiddleware(logger *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var bodyBytes []byte
		if r.Body != nil {
			var err error
			bodyBytes, err = io.ReadAll(r.Body)
			if err != nil {
				logger.Error("Failed to read request body", err)
			} else {
				r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
			}
		}
		logger.Info("Incoming request", "method", r.Method, "path", r.URL.Path, "remote", r.RemoteAddr, "body", string(bodyBytes))
		next.ServeHTTP(w, r)
	})
}

func unaryLoggingInterceptor(logger *slog.Logger) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		logger.Info("gRPC Unary Call", "method", info.FullMethod)
		return handler(ctx, req)
	}
}

func streamLoggingInterceptor(logger *slog.Logger) grpc.StreamServerInterceptor {
	return func(srv interface{}, ss grpc.ServerStream, info *grpc.StreamServerInfo, handler grpc.StreamHandler) error {
		logger.Info("gRPC Stream Call", "method", info.FullMethod)
		return handler(srv, ss)
	}
}

