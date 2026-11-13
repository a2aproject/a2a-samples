package itest_test

import (
	"fmt"
	"net"
	"os"
	"os/exec"
	"testing"
	"time"
)

func TestMain(m *testing.M) {
	if !listening("localhost:4222") || !listening("localhost:3306") {
		cmd := exec.Command("docker", "compose", "-f", "compose.yaml", "up", "-d")
		cmd.Dir = ".."
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "docker compose up failed: %v\n", err)
			os.Exit(1)
		}
	}
	os.Exit(m.Run())
}

func listening(addr string) bool {
	conn, err := net.DialTimeout("tcp", addr, time.Second)
	if err != nil {
		return false
	}
	if err := conn.Close(); err != nil {
		fmt.Fprintf(os.Stderr, "closing a connection to %s: %v\n", addr, err)
	}
	return true
}
