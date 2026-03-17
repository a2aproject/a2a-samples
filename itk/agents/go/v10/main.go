package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"iter"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"itk/agents/go/v10/pb"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2aclient"
	"github.com/a2aproject/a2a-go/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/a2acompat/a2av0"
	a2agrpc "github.com/a2aproject/a2a-go/a2agrpc/v1"
	"github.com/a2aproject/a2a-go/a2asrv"
	"golang.org/x/sync/errgroup"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/proto"
)

type V10AgentExecutor struct{}

func (e *V10AgentExecutor) Execute(ctx context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		log.Printf("Executing task %s", string(execCtx.TaskID))

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
			log.Printf("Error: %v", err)
			yield(a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(err.Error())), nil)
			return
		}

		results, err := e.handleInstruction(ctx, execCtx, instruction)
		if err != nil {
			log.Printf("Error handling instruction: %v", err)
			yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateFailed, nil), nil)
			return
		}

		response := strings.Join(results, "\n")
		if !yield(a2a.NewStatusUpdateEvent(execCtx, a2a.TaskStateCompleted, a2a.NewMessage(a2a.MessageRoleAgent, a2a.NewTextPart(response))), nil) {
			return
		}
	}
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
	log.Printf("Calling agent %s via %s", call.AgentCardUri, call.Transport)

	// 1. Resolve agent card
	resolver := agentcard.NewResolver(nil)
	resolver.CardParser = a2av0.NewAgentCardParser()
	card, err := resolver.Resolve(ctx, call.AgentCardUri)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve agent card for %s: %w", call.AgentCardUri, err)
	}

	// Print parsed card for debugging as requested
	if cardJSON, mErr := json.MarshalIndent(card, "", "  "); mErr == nil {
		log.Printf("Parsed Agent Card for %s:\n%s", call.AgentCardUri, string(cardJSON))
	} else {
		log.Printf("Warning: failed to marshal agent card for logging: %v", mErr)
	}

	protocol := mapTransport(call.Transport)
	log.Printf("Mapped transport: %s", protocol)

	// 3. Find all matching interfaces from the card
	matchedInterfaces := selectInterfaces(protocol, card)
	if len(matchedInterfaces) == 0 {
		return nil, fmt.Errorf("transport protocol %s is not supported by agent %s", protocol, call.AgentCardUri)
	}

	// 4. Create client using a factory
	// We instantiate a client through factory.CreateFromEndpoints
	// to strictly enforce the transport protocol. a2aclient.NewFromCard
	// seems to be using the first available transport if the specified one
	// is not supported.
	var factory *a2aclient.Factory
	compatFactory := a2av0.NewJSONRPCTransportFactory(a2av0.JSONRPCTransportConfig{})
	factory = a2aclient.NewFactory(
		a2agrpc.WithGRPCTransport(grpc.WithTransportCredentials(insecure.NewCredentials())),
		a2aclient.WithCompatTransport("0.3", a2a.TransportProtocolJSONRPC, compatFactory),
		a2aclient.WithCompatTransport("", a2a.TransportProtocolJSONRPC, compatFactory),
	)

	client, err := factory.CreateFromEndpoints(ctx, matchedInterfaces)
	if err != nil {
		return nil, fmt.Errorf("failed to create client: %w", err)
	}

	wrappedMsg, err := wrapInstructionToRequest(call.Instruction)
	if err != nil {
		return nil, fmt.Errorf("failed to wrap nested instruction: %w", err)
	}

	var responses []string
	if call.Streaming {
		events := client.SendStreamingMessage(ctx, &a2a.SendMessageRequest{Message: wrappedMsg})
		for ev, err := range events {
			if err != nil {
				log.Printf("Error inside streaming call to %s: %v", call.AgentCardUri, err)
				return nil, fmt.Errorf("streaming call failed to agent %s: %w", call.AgentCardUri, err)
			}
			responses = append(responses, extractResponses(ev)...)
		}
	} else {
		result, err := client.SendMessage(ctx, &a2a.SendMessageRequest{
			Message: wrappedMsg,
		})
		if err != nil {
			log.Printf("Error sending message to %s: %v", call.AgentCardUri, err)
			return nil, fmt.Errorf("failed to send message to agent %s: %w", call.AgentCardUri, err)
		}
		responses = extractResponses(result)
	}

	log.Printf("Received responses from %s", call.AgentCardUri)
	return responses, nil
}

func extractResponses(result any) []string {
	var responses []string
	log.Printf("Extracting responses from result of type %T", result)
	switch r := result.(type) {
	case *a2a.Message:
		for _, part := range r.Parts {
			if t := part.Text(); t != "" {
				responses = append(responses, t)
			}
		}
	case *a2a.Task:
		// Check both Status.Message and History
		if r.Status.Message != nil {
			for _, part := range r.Status.Message.Parts {
				if t := part.Text(); t != "" {
					responses = append(responses, t)
				}
			}
		}
		for _, msg := range r.History {
			if msg.Role == a2a.MessageRoleAgent {
				for _, part := range msg.Parts {
					if t := part.Text(); t != "" {
						responses = append(responses, t)
					}
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
		log.Printf("Warning: unexpected result type from SendMessage: %T", result)
	}
	return responses
}

func (e *V10AgentExecutor) Cancel(_ context.Context, execCtx *a2asrv.ExecutorContext) iter.Seq2[a2a.Event, error] {
	return func(yield func(a2a.Event, error) bool) {
		log.Printf("Cancel requested for task %s", string(execCtx.TaskID))
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
		log.Fatalf("Server session ended with error: %v", err)
	}
}

func run() error {
	flag.Parse()

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

	executor := &V10AgentExecutor{}
	requestHandler := a2asrv.NewHandler(executor)

	// Servers
	mux := http.NewServeMux()
	agentCardRoute := fmt.Sprintf("/jsonrpc%s", a2asrv.WellKnownAgentCardPath)
	mux.Handle("/", a2av0.NewJSONRPCHandler(requestHandler))
	mux.Handle("/jsonrpc", a2asrv.NewJSONRPCHandler(requestHandler))
	mux.Handle("/rest/", http.StripPrefix("/rest", a2asrv.NewRESTHandler(requestHandler)))

	cardProducer := a2av0.NewStaticAgentCardProducer(agentCard)
	mux.Handle(agentCardRoute, a2asrv.NewAgentCardHandler(cardProducer))

	httpServer := &http.Server{
		Addr:              fmt.Sprintf(":%d", *httpPort),
		Handler:           mux,
		ReadHeaderTimeout: 3 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	g, ctx := errgroup.WithContext(ctx)

	g.Go(func() error {
		serverType := "consolidated v1.0 & v0.3"
		log.Printf("Starting HTTP server on 127.0.0.1:%d (%s)", *httpPort, serverType)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			return err
		}
		return nil
	})

	grpcServer := grpc.NewServer()
	a2agrpc.NewHandler(requestHandler).RegisterWith(grpcServer)
	g.Go(func() error {
		lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *grpcPort))
		if err != nil {
			return err
		}
		log.Printf("Starting gRPC server on 127.0.0.1:%d", *grpcPort)
		return grpcServer.Serve(lis)
	})
	g.Go(func() error {
		<-ctx.Done()
		grpcServer.GracefulStop()
		return nil
	})

	// Wait for stop signal
	g.Go(func() error {
		<-ctx.Done()
		log.Println("Shutting down servers...")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return httpServer.Shutdown(shutdownCtx)
	})

	return g.Wait()
}
