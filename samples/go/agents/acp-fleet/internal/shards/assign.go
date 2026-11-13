// Package shards splits conversations into virtual shards and moves them
// between servers. A shard is a directory with a SQLite session map, the
// agent homes and the scratch directories of its conversations. Its record in
// the SHARDS KV bucket names the owner and lists the snapshots in the object
// store, and every save is a compare-and-swap on that record.
package shards

import (
	"crypto/sha256"
	"encoding/binary"
	"hash/fnv"
	"strconv"
)

// Of returns the shard of a conversation.
func Of(contextID string, count int) int {
	h := fnv.New32a()
	h.Write([]byte(contextID)) //nolint:errcheck // hash writes don't fail
	return int(h.Sum32() % uint32(count))
}

// Assign returns the server that should own the shard: the candidate with the
// highest rendezvous hash. When a server joins or leaves, only the shards it
// wins or loses move. It returns "" if there are no candidates.
func Assign(shard int, candidates []string) string {
	var best string
	var bestScore uint64
	for _, c := range candidates {
		sum := sha256.Sum256([]byte(c + "/" + strconv.Itoa(shard)))
		if score := binary.BigEndian.Uint64(sum[:8]); best == "" || score > bestScore {
			best, bestScore = c, score
		}
	}
	return best
}
