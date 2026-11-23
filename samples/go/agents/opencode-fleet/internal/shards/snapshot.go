package shards

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"sync"
	"time"

	"github.com/klauspost/compress/zstd"
	"github.com/nats-io/nats.go/jetstream"
	"golang.org/x/sync/errgroup"
)

// A snapshot of a directory is a manifest of its files, each a list of
// content-defined chunks. Chunks are stored once per conversation, named by
// the SHA-256 of their content and compressed one by one, so a snapshot
// uploads only the chunks that changed since the previous one.

// skipped are directories of caches that agents and tools write to their
// home, which are large and can be rebuilt.
var skipped = []string{".cache", ".npm", "node_modules"}

const transfers = 8

var (
	errTooLarge     = errors.New("directory is larger than the limit")
	errMissingChunk = errors.New("a chunk of the snapshot is missing")
)

var (
	encoder = must(zstd.NewWriter(nil, zstd.WithEncoderLevel(zstd.SpeedDefault)))
	decoder = must(zstd.NewReader(nil))
)

func must[T any](v T, err error) T {
	if err != nil {
		panic(err)
	}
	return v
}

type manifest struct {
	Files []fileEntry `json:"files"`
}

type fileEntry struct {
	Path   string      `json:"path"`
	Mode   fs.FileMode `json:"mode"`
	Size   int64       `json:"size,omitempty"`
	MTime  int64       `json:"mtime,omitempty"`
	Chunks []string    `json:"chunks,omitempty"`
}

// chunks returns the chunks of the manifests, which may be nil.
func chunks(ms ...*manifest) map[string]bool {
	set := map[string]bool{}
	for _, m := range ms {
		if m == nil {
			continue
		}
		for _, f := range m.Files {
			for _, c := range f.Chunks {
				set[c] = true
			}
		}
	}
	return set
}

// chunkStore holds the chunks and manifests of one conversation.
type chunkStore struct {
	obj    jetstream.ObjectStore
	prefix string
}

func (cs chunkStore) chunkName(hash string) string { return cs.prefix + "c/" + hash }

// snapshotResult is what [chunkStore.snapshot] did.
type snapshotResult struct {
	manifest *manifest
	// uploaded are the names of the chunks it uploaded, and bytes their compressed size.
	uploaded []string
	bytes    int64
	// size is the size of the files in the snapshot.
	size int64
}

// snapshot uploads the chunks of dir that aren't in known and returns the
// manifest of dir. Files whose size, mode and modification time match prev
// keep their chunks without being read.
func (cs chunkStore) snapshot(ctx context.Context, dir string, prev *manifest, known map[string]bool, limit int64) (snapshotResult, error) {
	previous := map[string]fileEntry{}
	if prev != nil {
		for _, f := range prev.Files {
			previous[f.Path] = f
		}
	}
	res := snapshotResult{manifest: &manifest{}}
	up := uploader{cs: cs, known: known, sent: map[string]bool{}}
	up.g, ctx = errgroup.WithContext(ctx)
	up.g.SetLimit(transfers)
	err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(dir, path)
		if err != nil || rel == "." {
			return err
		}
		if d.IsDir() && slices.Contains(skipped, d.Name()) {
			return filepath.SkipDir
		}
		if !d.IsDir() && !d.Type().IsRegular() {
			return nil
		}
		info, err := d.Info()
		if err != nil {
			return err
		}
		e := fileEntry{Path: filepath.ToSlash(rel), Mode: info.Mode()}
		if !d.IsDir() {
			e.Size, e.MTime = info.Size(), info.ModTime().UnixNano()
			if res.size += e.Size; res.size > limit {
				return errTooLarge
			}
			p, ok := previous[e.Path]
			if ok && p.Size == e.Size && p.MTime == e.MTime && p.Mode == e.Mode {
				e.Chunks = p.Chunks
			} else if e.Chunks, err = up.file(ctx, path); err != nil {
				return err
			}
		}
		res.manifest.Files = append(res.manifest.Files, e)
		return nil
	})
	err = errors.Join(err, up.g.Wait())
	res.uploaded, res.bytes = slices.Sorted(maps.Keys(up.sent)), up.bytes
	if err != nil {
		return res, fmt.Errorf("snapshot of %s: %w", dir, err)
	}
	return res, nil
}

type uploader struct {
	cs    chunkStore
	g     *errgroup.Group
	known map[string]bool

	mu    sync.Mutex
	sent  map[string]bool
	bytes int64
}

// file chunks the file, uploads its new chunks in the background and
// returns their hashes.
func (u *uploader) file(ctx context.Context, path string) (hashes []string, err error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer func() { err = errors.Join(err, f.Close()) }()
	c := newChunker(f)
	for {
		chunk, err := c.next()
		if errors.Is(err, io.EOF) {
			return hashes, nil
		}
		if err != nil {
			return nil, err
		}
		sum := sha256.Sum256(chunk)
		hash := hex.EncodeToString(sum[:])
		hashes = append(hashes, hash)
		u.mu.Lock()
		skip := u.known[hash] || u.sent[hash]
		if !skip {
			u.sent[hash] = true
		}
		u.mu.Unlock()
		if skip {
			continue
		}
		u.g.Go(func() error {
			data := encoder.EncodeAll(chunk, nil)
			if _, err := u.cs.obj.PutBytes(ctx, u.cs.chunkName(hash), data); err != nil {
				return fmt.Errorf("uploading a chunk: %w", err)
			}
			u.mu.Lock()
			u.bytes += int64(len(data))
			u.mu.Unlock()
			return nil
		})
	}
}

// putManifest uploads m as name.
func (cs chunkStore) putManifest(ctx context.Context, name string, m *manifest) (Object, error) {
	data, err := json.Marshal(m)
	if err != nil {
		return Object{}, err
	}
	data = encoder.EncodeAll(data, nil)
	if _, err := cs.obj.PutBytes(ctx, name, data); err != nil {
		return Object{}, fmt.Errorf("uploading %s: %w", name, err)
	}
	var size int64
	for _, f := range m.Files {
		size += f.Size
	}
	return Object{Name: name, Size: size, Saved: time.Now()}, nil
}

func getManifest(ctx context.Context, obj jetstream.ObjectStore, name string) (*manifest, error) {
	data, err := obj.GetBytes(ctx, name)
	if err != nil {
		return nil, err
	}
	if data, err = decoder.DecodeAll(data, nil); err != nil {
		return nil, fmt.Errorf("decompressing %s: %w", name, err)
	}
	var m manifest
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, fmt.Errorf("decoding %s: %w", name, err)
	}
	return &m, nil
}

// restore writes the files of m into dir. Paths can't leave dir.
func (cs chunkStore) restore(ctx context.Context, m *manifest, dir string) error {
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return err
	}
	root, err := os.OpenRoot(dir)
	if err != nil {
		return err
	}
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(transfers)
	for _, f := range m.Files {
		name := filepath.FromSlash(f.Path)
		if f.Mode.IsDir() {
			if err := root.MkdirAll(name, 0o700); err != nil {
				return errors.Join(err, root.Close())
			}
			continue
		}
		if parent := filepath.Dir(name); parent != "." {
			if err := root.MkdirAll(parent, 0o700); err != nil {
				return errors.Join(err, root.Close())
			}
		}
		g.Go(func() error { return cs.restoreFile(ctx, root, name, f) })
	}
	if err := g.Wait(); err != nil {
		return errors.Join(fmt.Errorf("restoring %s: %w", dir, err), root.Close())
	}
	return root.Close()
}

func (cs chunkStore) restoreFile(ctx context.Context, root *os.Root, name string, f fileEntry) error {
	out, err := root.OpenFile(name, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, f.Mode.Perm()|0o600)
	if err != nil {
		return err
	}
	for _, hash := range f.Chunks {
		if err := cs.writeChunk(ctx, out, hash); err != nil {
			return errors.Join(fmt.Errorf("%s: %w", f.Path, err), out.Close())
		}
	}
	if err := out.Close(); err != nil {
		return err
	}
	mtime := time.Unix(0, f.MTime)
	return root.Chtimes(name, mtime, mtime)
}

func (cs chunkStore) writeChunk(ctx context.Context, out *os.File, hash string) error {
	data, err := cs.obj.GetBytes(ctx, cs.chunkName(hash))
	if errors.Is(err, jetstream.ErrObjectNotFound) {
		return fmt.Errorf("%w: %s", errMissingChunk, hash)
	}
	if err != nil {
		return err
	}
	if data, err = decoder.DecodeAll(data, nil); err != nil {
		return err
	}
	if sum := sha256.Sum256(data); hex.EncodeToString(sum[:]) != hash {
		return fmt.Errorf("%w: chunk %s is corrupt", errMissingChunk, hash)
	}
	_, err = out.Write(data)
	return err
}
