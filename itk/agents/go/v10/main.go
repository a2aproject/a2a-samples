package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"bytes"
	"flag"
	"fmt"
	"io"
	"iter"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"itk/agents/go/v10/pb"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/v2/a2acompat/a2av0"
	a2agrpc "github.com/a2aproject/a2a-go/v2/a2agrpc/v1"
	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-go/v2/a2asrv/push"
	"github.com/a2aproject/a2a-go/v2/log"
	"golang.org/x/sync/errgroup"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/proto"
)

type V10AgentExecutor struct{}

func (e *V10AgentExecutor) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		log.Info(ctx, "Executing task", "taskId", string(execCtx.TaskID))

		if execCtx.StoredTask == nil {
			if !yield(a2a.NewSubmittedTask(execCtx, execCtx.Message), nil) {
				return
			}
		}

		if !yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateWorking, nil), nil) {
			return
		}

		instruction, err := extractInstruction(execCtx.Message)
		if err != nil {
			log.Error(ctx, "Error", err)
			yield(a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(err.Error())), nil)
			return
		}

		results, err := e.handleInstruction(ctx, execCtx, instruction)
		if err != nil {
			log.Error(ctx, "Error handling instruction", err)
			yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateFailed, nil), nil)
			return
		}

		response := strings.Join(results, "\n")
		if shouldHold(instruction) {
			log.Info(ctx, "Holding task as requested", "taskId", string(execCtx.TaskID))
			
			// Emitted event: response + task-finished
			log.Info(ctx, "Emitting response and task-finished", "taskId", string(execCtx.TaskID))
			if !yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateWorking, a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(response+"\ntask-finished"))), nil) {
				return
			}
			
			ticker := time.NewTicker(2 * time.Second)
			defer ticker.Stop()

			for i := 0; i < 5; i++ {
				select {
				case <-ctx.Done():
					log.Info(ctx, "Task cancelled, exiting hold loop", "taskId", string(execCtx.TaskID))
					return
				case <-ticker.C:
					log.Info(ctx, "Emitting periodic status update", "taskId", string(execCtx.TaskID))
					if !yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateWorking, nil), nil) {
						return
					}
				}
			}
			log.Info(ctx, "Held task timed out, auto-completing", "taskId", string(execCtx.TaskID))
		} else {
			if !yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCompleted, a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(response))), nil) {
				return
			}
		}
	}
}

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

func extractInstruction(msg *a2a.Message) (*pb.Instruction, error) {
	for _, part := range msg.Parts {
		if part.MediaType == "application/x-protobuf" || (part.MediaType == "" && part.Filename == "instruction.bin") {
			raw := part.Raw()
			if len(raw) > 0 {
				var instruction pb.Instruction
				if err := proto.Unmarshal(raw, &instruction); err == nil {
					return &instruction, nil
				}
			}
		}
		text := part.Text()
		if text != "" {
			if raw, err := base64.StdEncoding.DecodeString(text); err == nil {
				var instruction pb.Instruction
				if err := proto.Unmarshal(raw, &instruction); err == nil {
					return &instruction, nil
				}
			}
		}
	}
	return nil, fmt.Errorf("no valid instruction found in request")
}

func (e *V10AgentExecutor) handleInstruction(ctx context.Context, execCtx *a2asrv.ExecutorContext, inst *pb.Instruction) ([]string, error) {
	switch {
	case inst.GetCallAgent() != nil:
		return e.handleCallAgent(ctx, inst.GetCallAgent())

	case inst.GetReturnResponse() != nil:
		return []string{inst.GetReturnResponse().Response}, nil

	case inst.GetSteps() != nil:
		var allResults []string
		for _, step := range inst.GetSteps().Instructions {
			results, err := e.handleInstruction(ctx, execCtx, step)
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

func (e *V10AgentExecutor) handleCallAgent(ctx context.Context, call *pb.CallAgent) ([]string, error) {
	log.Info(ctx, "Calling agent", "agentCardUri", call.AgentCardUri, "transport", call.Transport)

	// 1. Resolve agent card
	resolver := agentcard.NewResolver(nil)
	resolver.CardParser = a2av0.NewAgentCardParser()
	card, err := resolver.Resolve(ctx, call.AgentCardUri)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve agent card for %s: %w", call.AgentCardUri, err)
	}

	// Print parsed card for debugging as requested
	if cardJSON, mErr := json.MarshalIndent(card, "", "  "); mErr == nil {
		log.Write(ctx, slog.LevelDebug, "Parsed Agent Card", "agentCardUri", call.AgentCardUri, "card", string(cardJSON))
	} else {
		log.Warn(ctx, "Failed to marshal agent card for logging", "error", mErr)
	}

	protocol := mapTransport(call.Transport)
	log.Info(ctx, "Mapped transport", "transport", protocol)

	// 3. Find all matching interfaces from the card
	matchedInterfaces := selectInterfaces(protocol, card)
	if len(matchedInterfaces) == 0 {
		return nil, fmt.Errorf("transport protocol %s is not supported by agent %s", protocol, call.AgentCardUri)
	}

	// 4. Create client using a factory
	var factory *a2aclient.Factory
	compatFactory := a2av0.NewJSONRPCTransportFactory(a2av0.JSONRPCTransportConfig{})
	
	clientOpts := []a2aclient.FactoryOption{
		a2agrpc.WithGRPCTransport(grpc.WithTransportCredentials(insecure.NewCredentials())),
		a2aclient.WithCompatTransport("0.3", a2a.TransportProtocolJSONRPC, compatFactory),
	}

	if call.GetPushNotification() != nil {
		url := call.GetPushNotification().GetUrl()
		if url == "" {
			return nil, fmt.Errorf("URL not specified in push_notification behavior")
		}
		clientOpts = append(clientOpts, a2aclient.WithConfig(a2aclient.Config{
			PushConfig: &a2a.PushConfig{
				URL:   fmt.Sprintf("%s/notifications", url),
				Token: "itk-token",
			},
		}))
	}

	factory = a2aclient.NewFactory(clientOpts...)

	client, err := factory.CreateFromEndpoints(ctx, matchedInterfaces)
	if err != nil {
		return nil, fmt.Errorf("failed to create client: %w", err)
	}

	wrappedMsg, err := wrapInstructionToRequest(call.Instruction)
	if err != nil {
		return nil, fmt.Errorf("failed to wrap nested instruction: %w", err)
	}

	var responses []string
	if call.GetResubscribe() != nil {
		return e.handleCallAgentWithResubscribe(ctx, client, wrappedMsg, call.AgentCardUri)
	} else if call.Streaming {
		events := client.SendStreamingMessage(ctx, &a2a.SendMessageRequest{Message: wrappedMsg})
		for ev, err := range events {
			if err != nil {
				log.Error(ctx, "Error inside streaming call", err, "agentCardUri", call.AgentCardUri)
				return nil, fmt.Errorf("streaming call failed to agent %s: %w", call.AgentCardUri, err)
			}
			responses = append(responses, extractResponses(ctx, ev)...)
		}
	} else {
		result, err := client.SendMessage(ctx, &a2a.SendMessageRequest{
			Message: wrappedMsg,
		})
		if err != nil {
			log.Error(ctx, "Error sending message", err, "agentCardUri", call.AgentCardUri)
			return nil, fmt.Errorf("failed to send message to agent %s: %w", call.AgentCardUri, err)
		}
		responses = extractResponses(ctx, result)
	}

	log.Info(ctx, "Received responses", "agentCardUri", call.AgentCardUri)
	return responses, nil
}

func (e *V10AgentExecutor) handleCallAgentWithResubscribe(ctx context.Context, client *a2aclient.Client, wrappedMsg *a2a.Message, agentCardUri string) ([]string, error) {
	log.Info(ctx, "Executing re-subscribe behavior in client", "agentCardUri", agentCardUri)

	initCtx, cancelInit := context.WithCancel(ctx)
	defer cancelInit()

	events := client.SendStreamingMessage(initCtx, &a2a.SendMessageRequest{Message: wrappedMsg})
	var taskID string

	for ev, err := range events {
		if err != nil {
			return nil, fmt.Errorf("initial call failed: %w", err)
		}
		switch r := ev.(type) {
		case *a2a.Task:
			taskID = string(r.ID)
		case *a2a.TaskStatusUpdateEvent:
			taskID = string(r.TaskID)
		}
		if taskID != "" {
			break
		}
	}

	cancelInit()
	log.Info(ctx, "Disconnected from task, now re-subscribing", "taskId", taskID)

	resubEvents := client.SubscribeToTask(ctx, &a2a.SubscribeToTaskRequest{ID: a2a.TaskID(taskID)})

	var taskObj *a2a.Task
	var responses []string
	for ev, err := range resubEvents {
		if err != nil {
			return nil, fmt.Errorf("resubscribe failed: %w", err)
		}
		if r, ok := ev.(*a2a.Task); ok {
			taskObj = r
			for _, msg := range r.History {
				if msg.Role == "ROLE_AGENT" || msg.Role == "agent" {
					for _, part := range msg.Parts {
						if t := part.Text(); t != "" {
							t = strings.ReplaceAll(t, "task-finished", "")
							responses = append(responses, t)
							if strings.Contains(part.Text(), "task-finished") {
								log.Info(ctx, "Found task-finished in history during loop, breaking.")
								goto EndLoop
							}
						}
					}
				}
			}
		}
		resps := extractResponses(ctx, ev)
		if len(resps) > 0 {
			for _, r := range resps {
				t := r
				t = strings.ReplaceAll(t, "task-finished", "")
				responses = append(responses, t)
				
				if strings.Contains(r, "task-finished") {
					log.Info(ctx, "Received task-finished after re-subscribe, breaking loop.")
					goto EndLoop
				}
			}
		}
	}
EndLoop:

	if len(responses) == 0 && taskObj != nil {
		log.Info(ctx, "Responses empty after loop, reading from history.")
		for _, msg := range taskObj.History {
			if msg.Role == "ROLE_AGENT" || msg.Role == "agent" {
				for _, part := range msg.Parts {
					if t := part.Text(); t != "" {
						t = strings.ReplaceAll(t, "task-finished", "")
						responses = append(responses, t)
					}
				}
			}
		}
	}

	log.Info(ctx, "Canceling task after retrieval", "taskId", taskID)
	_, err := client.CancelTask(ctx, &a2a.CancelTaskRequest{ID: a2a.TaskID(taskID)})
	if err != nil {
		return nil, fmt.Errorf("failed to cancel task after retrieval: %w", err)
	}

	return responses, nil
}

func extractResponses(ctx context.Context, result any) []string {
	var responses []string
	log.Write(ctx, slog.LevelDebug, "Extracting responses", "type", fmt.Sprintf("%T", result))
	switch r := result.(type) {
	case *a2a.Message:
		for _, part := range r.Parts {
			if t := part.Text(); t != "" {
				responses = append(responses, t)
			}
		}
	case *a2a.Task:
		if r.Status.Message != nil {
			for _, part := range r.Status.Message.Parts {
				if t := part.Text(); t != "" {
					responses = append(responses, t)
				}
			}
		}

	case *a2a.TaskStatusUpdateEvent:
		if r.Status.Message != nil {
			for _, part := range r.Status.Message.Parts {
				if t := part.Text(); t != "" {
					responses = append(responses, t)
				}
			}
		}
	default:
		log.Warn(ctx, "Unexpected result type from SendMessage", "type", fmt.Sprintf("%T", result))
	}
	return responses
}

func (e *V10AgentExecutor) Cancel(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		log.Info(ctx, "Cancel requested", "taskId", string(execCtx.TaskID))
		yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCanceled, nil), nil)
	}
}

func wrapInstructionToRequest(inst *pb.Instruction) (*a2a.Message, error) {
	instBytes, err := proto.Marshal(inst)
	if err != nil {
		return nil, err
	}

	part := a2a.NewRawPart(instBytes)
	part.Filename = "instruction.bin"
	part.MediaType = "application/x-protobuf"

	return a2a.NewMessage(a2a.MessageRoleUser, part), nil
}

func mapTransport(t string) a2a.TransportProtocol {
	switch strings.ToUpper(t) {
	case "GRPC":
		return a2a.TransportProtocolGRPC
	case "REST", "HTTP_JSON", "HTTP+JSON":
		return a2a.TransportProtocolHTTPJSON
	default:
		return a2a.TransportProtocolJSONRPC
	}
}

func selectInterfaces(protocol a2a.TransportProtocol, card *a2a.AgentCard) []*a2a.AgentInterface {
	var matched []*a2a.AgentInterface
	for _, iface := range card.SupportedInterfaces {
		if iface.ProtocolBinding == protocol {
			iface.URL = strings.TrimSuffix(iface.URL, "/")
			matched = append(matched, iface)
		}
	}
	return matched
}



var httpPort = flag.Int("httpPort", 10102, "HTTP port")
var grpcPort = flag.Int("grpcPort", 11002, "gRPC port")

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

	jsonRPCV0Addr := fmt.Sprintf("http://127.0.0.1:%d", *httpPort)

	agentCard := &a2a.AgentCard{
		Name:               "ITK v10 Agent",
		Description:        "Multi-transport Go agent with A2A v0.3 compatibility.",
		Version:            "1.0.0-alpha",
		Capabilities:       a2a.AgentCapabilities{Streaming: true},
		DefaultInputModes:  []string{"text"},
		DefaultOutputModes: []string{"text"},
		SupportedInterfaces: []*a2a.AgentInterface{
			{
				URL:             fmt.Sprintf("http://127.0.0.1:%d/jsonrpc", *httpPort),
				ProtocolBinding: a2a.TransportProtocolJSONRPC,
				ProtocolVersion: a2a.Version,
			},
			{
				URL:             jsonRPCV0Addr,
				ProtocolBinding: a2a.TransportProtocolJSONRPC,
				ProtocolVersion: a2av0.Version,
			},
			{
				URL:             fmt.Sprintf("http://127.0.0.1:%d/rest", *httpPort),
				ProtocolBinding: a2a.TransportProtocolHTTPJSON,
				ProtocolVersion: a2a.Version,
			},
			{
				URL:             fmt.Sprintf("127.0.0.1:%d", *grpcPort),
				ProtocolBinding: a2a.TransportProtocolGRPC,
				ProtocolVersion: a2a.Version,
			},
		},
	}

	pushStore := push.NewInMemoryStore()
	pushSender := push.NewHTTPPushSender(nil)

	executor := &V10AgentExecutor{}
	requestHandler := a2asrv.NewHandler(
		executor,
		a2asrv.WithCallInterceptors(a2asrv.NewLoggingInterceptor(&a2asrv.LoggingConfig{LogPayload: true})),
		a2asrv.WithPushNotifications(pushStore, pushSender),
	)

	mux := http.NewServeMux()
	agentCardRoute := fmt.Sprintf("/jsonrpc%s", a2asrv.WellKnownAgentCardPath)
	mux.Handle("/", a2av0.NewJSONRPCHandler(requestHandler))
	mux.Handle("/jsonrpc", a2asrv.NewJSONRPCHandler(requestHandler))
	mux.Handle("/rest/", http.StripPrefix("/rest", a2asrv.NewRESTHandler(requestHandler)))

	cardProducer := a2av0.NewStaticAgentCardProducer(agentCard)
	mux.Handle(agentCardRoute, a2asrv.NewAgentCardHandler(cardProducer))

	httpServer := &http.Server{
		Addr:              fmt.Sprintf(":%d", *httpPort),
		Handler:           loggingMiddleware(logger, mux),
		ReadHeaderTimeout: 3 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	ctx = log.AttachLogger(ctx, logger)

	g, ctx := errgroup.WithContext(ctx)

	g.Go(func() error {
		serverType := "consolidated v1.0 & v0.3"
		log.Info(ctx, "Starting HTTP server", "address", fmt.Sprintf("127.0.0.1:%d", *httpPort), "type", serverType)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			return err
		}
		return nil
	})

	grpcServer := grpc.NewServer(
		grpc.UnaryInterceptor(unaryLoggingInterceptor(logger)),
		grpc.StreamInterceptor(streamLoggingInterceptor(logger)),
	)
	a2agrpc.NewHandler(requestHandler).RegisterWith(grpcServer)
	g.Go(func() error {
		lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *grpcPort))
		if err != nil {
			return err
		}
		log.Info(ctx, "Starting gRPC server", "address", fmt.Sprintf("127.0.0.1:%d", *grpcPort))
		return grpcServer.Serve(lis)
	})
	g.Go(func() error {
		<-ctx.Done()
		grpcServer.GracefulStop()
		return nil
	})

	g.Go(func() error {
		<-ctx.Done()
		log.Info(ctx, "Shutting down servers")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return httpServer.Shutdown(shutdownCtx)
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

