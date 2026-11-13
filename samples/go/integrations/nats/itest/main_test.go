package itest_test

import (
	"fmt"
	"os"
	"os/exec"
	"testing"

	"github.com/a2aproject/a2a-samples/samples/go/integrations/nats/natstest"
	"github.com/nats-io/nats.go"
)

func TestMain(m *testing.M) {
	if nc, err := nats.Connect(natstest.URL); err == nil {
		nc.Close()
		os.Exit(m.Run())
	}
	cmd := exec.Command("docker", "compose", "-f", "compose.yaml", "up", "-d")
	cmd.Dir = ".."
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "docker compose up failed: %v\n", err)
		os.Exit(1)
	}
	os.Exit(m.Run())
}
