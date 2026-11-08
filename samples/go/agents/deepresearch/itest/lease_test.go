package itest_test

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/lease"
	"github.com/a2aproject/a2a-samples/samples/go/agents/deepresearch/internal/testutil"
	"github.com/nats-io/nats.go/jetstream"
)

func TestLease_AcquireAfterHolderStopsRenewing(t *testing.T) {
	testutil.SetupNATS(t)
	_, js := testutil.ConnectNATS(t)

	tests := []struct {
		name          string
		bucketExisted bool
	}{
		{name: "new bucket"},
		{name: "bucket created without TTL markers", bucketExisted: true},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
			t.Cleanup(cancel)

			cfg := jetstream.KeyValueConfig{Bucket: "LEASE_TEST", TTL: 2 * time.Second}
			if err := js.DeleteKeyValue(ctx, cfg.Bucket); err != nil && !errors.Is(err, jetstream.ErrBucketNotFound) {
				t.Fatalf("js.DeleteKeyValue() error = %v", err)
			}
			if tc.bucketExisted {
				if _, err := js.CreateKeyValue(ctx, cfg); err != nil {
					t.Fatalf("js.CreateKeyValue() error = %v", err)
				}
			}
			holder, err := lease.CreateManager(ctx, js, cfg)
			if err != nil {
				t.Fatalf("lease.CreateManager() error = %v", err)
			}
			standby, err := lease.CreateManager(ctx, js, cfg)
			if err != nil {
				t.Fatalf("lease.CreateManager() error = %v", err)
			}

			if _, err := holder.Acquire(ctx, "leader", "holder"); err != nil {
				t.Fatalf("holder.Acquire() error = %v", err)
			}

			start := time.Now()
			acquireCtx, cancelAcquire := context.WithTimeout(ctx, 10*time.Second)
			defer cancelAcquire()
			if _, err := standby.Acquire(acquireCtx, "leader", "standby"); err != nil {
				t.Fatalf("standby.Acquire() after %v error = %v, want the lease once the holder's expires", time.Since(start), err)
			}
		})
	}
}
