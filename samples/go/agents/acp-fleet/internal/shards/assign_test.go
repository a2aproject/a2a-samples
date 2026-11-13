package shards_test

import (
	"testing"

	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/shards"
)

func TestAssign_movesOnlyTheShardsOfTheChangedServer(t *testing.T) {
	t.Parallel()
	const count = 64
	three := []string{"server-1", "server-2", "server-3"}
	four := append(append([]string{}, three...), "server-4")

	moved, perServer := 0, map[string]int{}
	for s := range count {
		before, after := shards.Assign(s, three), shards.Assign(s, four)
		perServer[before]++
		if before != after {
			moved++
			if after != "server-4" {
				t.Fatalf("Assign(%d) moved from %s to %s, want only moves to server-4", s, before, after)
			}
		}
	}
	if moved == 0 || moved > count/2 {
		t.Fatalf("Assign() moved %d of %d shards when server-4 joined, want about a quarter", moved, count)
	}
	for _, name := range three {
		if perServer[name] < count/6 {
			t.Fatalf("Assign() gave %s %d of %d shards, want a fair share", name, perServer[name], count)
		}
	}
	if got := shards.Assign(0, nil); got != "" {
		t.Fatalf("Assign(0, nil) = %q, want \"\"", got)
	}
}

func TestOf_isStable(t *testing.T) {
	t.Parallel()
	if a, b := shards.Of("ctx-1", 64), shards.Of("ctx-1", 64); a != b || a < 0 || a >= 64 {
		t.Fatalf("Of(ctx-1) = %d, %d, want the same shard in [0, 64)", a, b)
	}
}
