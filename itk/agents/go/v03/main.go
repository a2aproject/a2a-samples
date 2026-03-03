package main

import (
	"context"
	"encoding/base64"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"itk/agents/go/v03/pb"

	"github.com/a2aproject/a2a-go/a2a"
	"github.com/a2aproject/a2a-go/a2aclient"
	"github.com/a2aproject/a2a-go/a2aclient/agentcard"
	"github.com/a2aproject/a2a-go/a2asrv"
	"github.com/a2aproject/a2a-go/a2asrv/eventqueue"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/proto"

	"github.com/a2aproject/a2a-go/a2agrpc"
	"golang.org/x/sync/errgroup"
)

type V03AgentExecutor struct {
}

func (e *V03AgentExecutor) Execute(ctx context.Context, reqCtx *a2asrv.RequestContext, queue eventqueue.Queue) error {
	log.Printf("Executing task %s", reqCtx.Message.ID)

	// 1. Extract Instruction from message parts
	var instruction pb.Instruction
	found := false
	for _, part := range reqCtx.Message.Parts {
		if filePart, ok := part.(a2a.FilePart); ok {
			if fileBytes, ok := filePart.File.(a2a.FileBytes); ok {
				rawBytes, err := base64.StdEncoding.DecodeString(fileBytes.Bytes)
				if err != nil {
					log.Printf("Failed to decode base64 bytes: %v", err)
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
		log.Println(errMsg)
		return queue.Write(ctx, a2a.NewMessageForTask(a2a.MessageRoleAgent, reqCtx, a2a.TextPart{Text: errMsg}))
	}

	// 2. Handle Instruction
	results, err := e.handleInstruction(ctx, reqCtx, &instruction)
	if err != nil {
		log.Printf("Error handling instruction: %v", err)
		return queue.Write(ctx, a2a.NewMessageForTask(a2a.MessageRoleAgent, reqCtx, a2a.TextPart{Text: fmt.Sprintf("Execution Error: %v", err)}))
	}

	// 3. Return response
	response := strings.Join(results, "\n")
	return queue.Write(ctx, a2a.NewMessageForTask(a2a.MessageRoleAgent, reqCtx, a2a.TextPart{Text: response}))
}

func (e *V03AgentExecutor) handleInstruction(ctx context.Context, reqCtx *a2asrv.RequestContext, inst *pb.Instruction) ([]string, error) {
	switch {
	case inst.GetCallAgent() != nil:
		call := inst.GetCallAgent()
		log.Printf("Calling agent %s via %s", call.AgentCardUri, call.Transport)

		// Resolve card and create client
		card, err := agentcard.DefaultResolver.Resolve(ctx, call.AgentCardUri)
		if err != nil {
			return nil, fmt.Errorf("failed to resolve agent card for %s: %w", call.AgentCardUri, err)
		}
		// 3. Create client with optional transport enforcement
		opts := []a2aclient.FactoryOption{
			a2aclient.WithGRPCTransport(grpc.WithTransportCredentials(insecure.NewCredentials())),
		}

		tp := mapTransport(call.Transport)
		tURL := getTransportURL(call.Transport, card)
		log.Printf("Mapped transport: %s", tp)

		client, err := a2aclient.NewFromEndpoints(ctx, []a2a.AgentInterface{{URL: tURL, Transport: tp}}, opts...)
		if err != nil {
			return nil, fmt.Errorf("failed to connect to agent %s: %w", call.AgentCardUri, err)
		}

		// Wrap instruction back to a message
		wrappedMsg, err := wrapInstructionToRequest(call.Instruction)
		if err != nil {
			return nil, fmt.Errorf("failed to wrap nested instruction: %w", err)
		}

		// Perform the call
		result, err := client.SendMessage(ctx, wrappedMsg)

		if err != nil {
			return nil, fmt.Errorf("failed to send message to agent %s: %w", call.AgentCardUri, err)
		}

		var responses []string
		if msg, ok := result.(*a2a.Message); ok {
			for _, part := range msg.Parts {
				if textPart, ok := part.(a2a.TextPart); ok {
					responses = append(responses, textPart.Text)
				}
			}
		} else {
			return nil, fmt.Errorf("unexpected result type from SendMessage: %T", result)
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

func (e *V03AgentExecutor) Cancel(_ context.Context, reqCtx *a2asrv.RequestContext, _ eventqueue.Queue) error {
	log.Printf("Cancel requested for task %s", reqCtx.Message.ID)
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

func getTransportURL(t string, card *a2a.AgentCard) string {
	tEnum := mapTransport(t)
	for _, iface := range card.AdditionalInterfaces {
		if iface.Transport == tEnum {
			return iface.URL
		}
	}
	return card.URL
}

var httpPort = flag.Int("httpPort", 10101, "HTTP port")
var grpcPort = flag.Int("grpcPort", 11001, "gRPC port")

func main() {
	if err := run(); err != nil {
		log.Fatalf("Server session ended with error: %v", err)
	}
}

func run() error {
	flag.Parse()

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

	// go-sdk v.03 has support for JSONRPC and GRPC only
	agentCard := &a2a.AgentCard{
		Name:               "ITK v03 Agent",
		Description:        "Multi-transport agent supporting raw Instruction protos.",
		URL:                jsonRPCAddr,
		Version:            "0.3.0",
		DefaultInputModes:  []string{"text"},
		DefaultOutputModes: []string{"text"},
		Capabilities:       a2a.AgentCapabilities{Streaming: false},
		Skills:             []a2a.AgentSkill{skill},
		AdditionalInterfaces: []a2a.AgentInterface{
			{URL: grpcAddr, Transport: a2a.TransportProtocolGRPC},
		},
	}

	executor := &V03AgentExecutor{}
	requestHandler := a2asrv.NewHandler(executor, a2asrv.WithExtendedAgentCard(agentCard))

	// 1. JSON-RPC handler
	jsonrpcHandler := a2asrv.NewJSONRPCHandler(requestHandler)
	cardHandler := a2asrv.NewStaticAgentCardHandler(agentCard)

	mux := http.NewServeMux()
	mux.Handle(a2asrv.WellKnownAgentCardPath, cardHandler)
	mux.Handle("/jsonrpc", jsonrpcHandler)

	httpServer := &http.Server{
		Addr:              host + ":" + fmt.Sprintf("%d", *httpPort),
		Handler:           mux,
		ReadHeaderTimeout: 3 * time.Second,
	}

	// 2. gRPC handler
	grpcServer := grpc.NewServer()
	grpcHandler := a2agrpc.NewHandler(requestHandler)
	grpcHandler.RegisterWith(grpcServer)

	// 3. Run servers concurrently
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	g, ctx := errgroup.WithContext(ctx)

	g.Go(func() error {
		log.Printf("Starting HTTP server on %s:%d (JSON-RPC)", host, *httpPort)
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
		log.Printf("Starting gRPC server on %s:%d", host, *grpcPort)
		if err := grpcServer.Serve(lis); err != nil {
			return fmt.Errorf("gRPC server failed: %w", err)
		}
		return nil
	})

	g.Go(func() error {
		<-ctx.Done()
		log.Println("Shutting down servers...")

		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err := httpServer.Shutdown(shutdownCtx); err != nil {
			log.Printf("HTTP server shutdown error: %v", err)
		}

		grpcServer.GracefulStop()
		log.Println("Servers closed.")
		return nil
	})

	return g.Wait()
}
