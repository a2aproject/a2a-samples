package shards

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"errors"
	"io"
	"testing"
)

func split(t *testing.T, data []byte) [][32]byte {
	t.Helper()
	var sums [][32]byte
	c := newChunker(bytes.NewReader(data))
	total := 0
	for {
		chunk, err := c.next()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			t.Fatalf("chunker.next() error = %v", err)
		}
		if len(chunk) > maxChunk {
			t.Fatalf("chunker.next() = %d bytes, want at most %d", len(chunk), maxChunk)
		}
		total += len(chunk)
		sums = append(sums, sha256.Sum256(chunk))
	}
	if total != len(data) {
		t.Fatalf("chunks have %d bytes, want %d", total, len(data))
	}
	return sums
}

func TestChunker_insertionChangesOnlyNearbyChunks(t *testing.T) {
	t.Parallel()
	data := make([]byte, 4<<20)
	if _, err := rand.Read(data); err != nil {
		t.Fatalf("rand.Read() error = %v", err)
	}
	edited := append(append(append([]byte{}, data[:1<<20]...), []byte("inserted text")...), data[1<<20:]...)

	before, after := split(t, data), split(t, edited)
	kept := map[[32]byte]bool{}
	for _, s := range before {
		kept[s] = true
	}
	changed := 0
	for _, s := range after {
		if !kept[s] {
			changed++
		}
	}
	if len(before) < 20 {
		t.Fatalf("split() = %d chunks of 4 MiB, want about 50", len(before))
	}
	if changed > 2 {
		t.Fatalf("an insertion changed %d of %d chunks, want at most 2", changed, len(after))
	}
}

func TestChunker_emptyInput(t *testing.T) {
	t.Parallel()
	if got := split(t, nil); len(got) != 0 {
		t.Fatalf("split(nil) = %d chunks, want 0", len(got))
	}
}
