package timestamp_ext

import (
	"context"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
)

var messagingMethods = map[string]bool{
	"SendMessage":          true,
	"SendStreamingMessage": true,
}

// ClientInterceptor returns a client call interceptor that requests this extension.
func ClientInterceptor(ext *TimestampExtension) a2aclient.CallInterceptor {
	return &timestampingClientInterceptor{ext: ext}
}

// timestampingClientInterceptor is a client interceptor that adds timestamps to outgoing messages.
//
// It also requests the timestamp extension via the A2A-Extensions header.
type timestampingClientInterceptor struct {
	a2aclient.PassthroughInterceptor
	ext *TimestampExtension
}

func (i *timestampingClientInterceptor) Before(ctx context.Context, req *a2aclient.Request) (context.Context, any, error) {
	if !i.ext.IsSupported(req.Card) || !messagingMethods[req.Method] {
		return ctx, nil, nil
	}

	if smReq, ok := req.Payload.(*a2a.SendMessageRequest); ok && smReq != nil && smReq.Message != nil {
		i.ext.ApplyTimestamp(smReq.Message)
	}

	if req.ServiceParams == nil {
		req.ServiceParams = make(a2aclient.ServiceParams)
	}
	req.ServiceParams.Append(a2a.SvcParamExtensions, URI)

	return ctx, nil, nil
}
