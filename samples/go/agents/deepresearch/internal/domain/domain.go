// Package domain defines shared types used across all agent packages.
package domain

import (
	"context"

	"github.com/a2aproject/a2a-go/v2/a2asrv"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/utils"
)

// AgentType identifies the role of an agent in the deep research system.
type AgentType string

const (
	AgentOrchestrator AgentType = "orchestrator"
	AgentResearcher   AgentType = "researcher"
	AgentAnalyzer     AgentType = "analyzer"
	AgentSynthesizer  AgentType = "synthesizer"
)

type nodeInfoKeyType struct{}

// NodeInfo holds node metadata.
type NodeInfo struct {
	Agent AgentType
}

// NodeInfoFrom extracts [NodeInfo] from the given context.
func NodeInfoFrom(ctx context.Context) NodeInfo {
	if ni, ok := ctx.Value(nodeInfoKeyType{}).(NodeInfo); ok {
		return ni
	}
	return NodeInfo{}
}

// NodeInfoFrom extracts [Info] from the given context.
func WithNodeInfo(ni NodeInfo) a2asrv.RequestHandlerOption {
	return a2asrv.WithCallInterceptors(&interceptor{nodeInfo: ni})
}

type interceptor struct {
	nodeInfo NodeInfo
	a2asrv.PassthroughCallInterceptor
}

// Before implements [a2asrv.CallInterceptor.Before].
func (i *interceptor) Before(ctx context.Context, callCtx *a2asrv.CallContext, req *a2asrv.Request) (context.Context, any, error) {
	return context.WithValue(ctx, nodeInfoKeyType{}, i.nodeInfo), nil, nil
}

// ContextCodec implements [a2asrv.ContextCodec].
type ContextCodec struct{}

// Encode implements [a2asrv.ContextCodec.Encode].
func (cc *ContextCodec) Encode(ctx context.Context) (map[string]any, error) {
	return utils.ToMapStruct(NodeInfoFrom(ctx))
}

// Decode implements [a2asrv.ContextCodec.Decode].
func (cc *ContextCodec) Decode(ctx context.Context, encoded map[string]any) (context.Context, error) {
	nodeInfoMap, err := utils.FromMapStruct[NodeInfo](encoded)
	if err != nil {
		return nil, err
	}
	return context.WithValue(ctx, nodeInfoKeyType{}, nodeInfoMap), nil
}
