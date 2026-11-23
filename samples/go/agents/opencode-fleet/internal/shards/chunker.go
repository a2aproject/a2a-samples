package shards

import (
	"bytes"
	"errors"
	"io"
)

// Content-defined chunking with a gear hash, as in FastCDC: a boundary falls
// where the hash of the last 64 bytes matches a mask, so an insertion moves
// only the boundaries around it and the other chunks keep their hashes.
const (
	minChunk = 16 << 10
	maxChunk = 256 << 10
	// The average chunk is minChunk + 64 KiB.
	maskBits = 16
	mask     = (1<<maskBits - 1) << (64 - maskBits)
)

var gear = func() (table [256]uint64) {
	// splitmix64 with a fixed seed: boundaries must be the same on every server.
	x := uint64(0x9e3779b97f4a7c15)
	for i := range table {
		x += 0x9e3779b97f4a7c15
		z := x
		z = (z ^ z>>30) * 0xbf58476d1ce4e5b9
		z = (z ^ z>>27) * 0x94d049bb133111eb
		table[i] = z ^ z>>31
	}
	return table
}()

type chunker struct {
	r   io.Reader
	buf []byte
	n   int
	eof bool
}

func newChunker(r io.Reader) *chunker {
	return &chunker{r: r, buf: make([]byte, maxChunk)}
}

// next returns the next chunk, or io.EOF after the last one.
func (c *chunker) next() ([]byte, error) {
	for c.n < maxChunk && !c.eof {
		m, err := c.r.Read(c.buf[c.n:])
		c.n += m
		if errors.Is(err, io.EOF) {
			c.eof = true
		} else if err != nil {
			return nil, err
		}
	}
	if c.n == 0 {
		return nil, io.EOF
	}
	cut := boundary(c.buf[:c.n])
	chunk := bytes.Clone(c.buf[:cut])
	c.n = copy(c.buf, c.buf[cut:c.n])
	return chunk, nil
}

func boundary(b []byte) int {
	if len(b) <= minChunk {
		return len(b)
	}
	var h uint64
	for i := minChunk; i < len(b); i++ {
		h = h<<1 + gear[b[i]]
		if h&mask == 0 {
			return i + 1
		}
	}
	return len(b)
}
