package shards

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"maps"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/nats-io/nats.go/jetstream"
	_ "modernc.org/sqlite" // SQLite driver registration
)

// ErrLost is returned once another server owns the shard.
var ErrLost = errors.New("the shard moved to another server")

// Shard is a shard this server owns.
type Shard struct {
	ID    int
	dir   string
	table *Table
	limit int64
	// scratchLimit caps the scratch snapshots taken after every turn.
	scratchLimit int64

	mu   sync.Mutex
	rec  Record
	rev  uint64
	seq  int
	db   *sql.DB
	lost bool
	// manifests are the manifests of the record's snapshots by context ID,
	// loaded on first use.
	manifests map[string]*snapshots
}

// snapshots are the manifests of a conversation's home and scratch directory.
type snapshots struct {
	home, scratch *manifest
}

func (s *Shard) store(contextID string) chunkStore {
	return chunkStore{obj: s.table.obj, prefix: fmt.Sprintf("%s/%s/", key(s.ID), filepath.Base(contextID))}
}

// snapshotsLocked returns the manifests of the conversation's snapshots in the record.
func (s *Shard) snapshotsLocked(ctx context.Context, contextID string) (*snapshots, error) {
	if m, ok := s.manifests[contextID]; ok {
		return m, nil
	}
	m := &snapshots{}
	var err error
	if obj, ok := s.rec.Homes[contextID]; ok {
		if m.home, err = s.loadManifest(ctx, obj); err != nil {
			return nil, err
		}
	}
	if obj, ok := s.rec.Scratch[contextID]; ok {
		if m.scratch, err = s.loadManifest(ctx, obj); err != nil {
			return nil, err
		}
	}
	if s.manifests == nil {
		s.manifests = map[string]*snapshots{}
	}
	s.manifests[contextID] = m
	return m, nil
}

// loadManifest returns the manifest, or nil if it expired.
func (s *Shard) loadManifest(ctx context.Context, obj Object) (*manifest, error) {
	m, err := getManifest(ctx, s.table.obj, obj.Name)
	if errors.Is(err, jetstream.ErrObjectNotFound) {
		log.Warn(ctx, "snapshot is missing, starting empty", "object", obj.Name)
		return nil, nil
	}
	return m, err
}

// Epoch returns the epoch of this server's claim.
func (s *Shard) Epoch() uint64 {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.rec.Epoch
}

// HomeDir returns the agent home of the conversation.
func (s *Shard) HomeDir(contextID string) string {
	return filepath.Join(s.dir, "homes", filepath.Base(contextID))
}

// ScratchDir returns the scratch directory of the conversation.
func (s *Shard) ScratchDir(contextID string) string {
	return filepath.Join(s.dir, "scratch", filepath.Base(contextID))
}

// Prepare restores the agent home and the scratch directory of the
// conversation from their snapshots if this server doesn't have them yet.
// It reports whether the scratch directory was lost: the home has a snapshot
// and the scratch directory has none, because it outgrew the scratch limit
// before the conversation moved without a graceful release.
func (s *Shard) Prepare(ctx context.Context, contextID string) (scratchLost bool, err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.lost {
		return false, ErrLost
	}
	snaps, err := s.snapshotsLocked(ctx, contextID)
	if err != nil {
		return false, err
	}
	home, scratch := s.HomeDir(contextID), s.ScratchDir(contextID)
	homeRestored := false
	if _, err := os.Stat(home); errors.Is(err, os.ErrNotExist) {
		if err := s.restore(ctx, contextID, snaps.home, home); err != nil {
			return false, err
		}
		homeRestored = snaps.home != nil
	}
	if _, err := os.Stat(scratch); !errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	if err := s.restore(ctx, contextID, snaps.scratch, scratch); err != nil {
		return false, err
	}
	return homeRestored && snaps.scratch == nil, nil
}

// restore writes the snapshot m into dir, or creates dir empty if m is nil
// or broken.
func (s *Shard) restore(ctx context.Context, contextID string, m *manifest, dir string) error {
	if m == nil {
		return os.MkdirAll(dir, 0o700)
	}
	err := s.store(contextID).restore(ctx, m, dir)
	if errors.Is(err, errMissingChunk) {
		log.Warn(ctx, "snapshot is broken, starting empty", "dir", dir, "cause", err)
		return errors.Join(os.RemoveAll(dir), os.MkdirAll(dir, 0o700))
	}
	return err
}

// Session returns the ACP session of the conversation.
func (s *Shard) Session(ctx context.Context, contextID string) (sessionID, agentKey string, ok bool, err error) {
	db, err := s.database()
	if err != nil {
		return "", "", false, err
	}
	err = db.QueryRowContext(ctx, `SELECT session_id, agent_key FROM sessions WHERE context_id = ?`, contextID).Scan(&sessionID, &agentKey)
	if errors.Is(err, sql.ErrNoRows) {
		return "", "", false, nil
	}
	return sessionID, agentKey, err == nil, err
}

// PutSession records the ACP session of the conversation.
func (s *Shard) PutSession(ctx context.Context, contextID, sessionID, agentKey string) error {
	db, err := s.database()
	if err != nil {
		return err
	}
	_, err = db.ExecContext(ctx, `INSERT INTO sessions (context_id, session_id, agent_key, updated_at) VALUES (?, ?, ?, ?)
		ON CONFLICT (context_id) DO UPDATE SET session_id = excluded.session_id, agent_key = excluded.agent_key, updated_at = excluded.updated_at`,
		contextID, sessionID, agentKey, time.Now().Unix())
	return err
}

func (s *Shard) database() (*sql.DB, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.lost {
		return nil, ErrLost
	}
	return s.db, nil
}

// Saved describes what [Shard.Save] uploaded.
type Saved struct {
	// Uploaded is the compressed size of the new chunks, and Size the size
	// of the files in the snapshots.
	Uploaded int64
	Size     int64
	// ScratchSaved is false when the scratch directory outgrew the scratch
	// limit, so it moves only with a graceful release.
	ScratchSaved bool
}

// Save uploads snapshots of the conversation's agent home, its scratch
// directory if it is within the scratch limit, and the session map.
func (s *Shard) Save(ctx context.Context, contextID string) (Saved, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.lost {
		return Saved{}, ErrLost
	}
	prev, err := s.snapshotsLocked(ctx, contextID)
	if err != nil {
		return Saved{}, err
	}
	cs := s.store(contextID)
	known := chunks(prev.home, prev.scratch)
	var saved Saved
	var created []string
	home, err := cs.snapshot(ctx, s.HomeDir(contextID), prev.home, known, s.limit)
	if err != nil {
		return Saved{}, err
	}
	saved.Uploaded, saved.Size = home.bytes, home.size
	next := s.rec.clone()
	if next.Homes == nil {
		next.Homes = map[string]Object{}
	}
	if next.Scratch == nil {
		next.Scratch = map[string]Object{}
	}
	homeObj, err := cs.putManifest(ctx, s.manifestName(contextID, "home"), home.manifest)
	if err != nil {
		return Saved{}, err
	}
	next.Homes[contextID] = homeObj
	created = append(created, homeObj.Name)
	snaps := &snapshots{home: home.manifest}

	scratch, err := cs.snapshot(ctx, s.ScratchDir(contextID), prev.scratch, maps.Clone(known), s.scratchLimit)
	saved.Uploaded += scratch.bytes
	switch {
	case errors.Is(err, errTooLarge):
		delete(next.Scratch, contextID)
	case err != nil:
		s.deleteObjects(ctx, created)
		return Saved{}, err
	default:
		obj, err := cs.putManifest(ctx, s.manifestName(contextID, "scratch"), scratch.manifest)
		if err != nil {
			s.deleteObjects(ctx, created)
			return Saved{}, err
		}
		next.Scratch[contextID] = obj
		created = append(created, obj.Name)
		snaps.scratch = scratch.manifest
		saved.Size += scratch.size
		saved.ScratchSaved = true
	}
	sessions, err := s.putSessions(ctx)
	if err != nil {
		s.deleteObjects(ctx, created)
		return Saved{}, err
	}
	next.Sessions = sessions
	created = append(created, sessions.Name)
	if err := s.commitLocked(ctx, next, created); err != nil {
		return Saved{}, err
	}
	s.replaceSnapshotsLocked(ctx, contextID, prev, snaps)
	return saved, nil
}

// replaceSnapshotsLocked records the conversation's new snapshots and deletes
// the chunks only the old ones had. Call it after the record points at next.
func (s *Shard) replaceSnapshotsLocked(ctx context.Context, contextID string, prev, next *snapshots) {
	keep := chunks(next.home, next.scratch)
	cs := s.store(contextID)
	var unused []string
	for hash := range chunks(prev.home, prev.scratch) {
		if !keep[hash] {
			unused = append(unused, cs.chunkName(hash))
		}
	}
	s.deleteObjects(ctx, unused)
	s.manifests[contextID] = next
}

// release uploads the scratch directories up to the snapshot limit and the
// session map, frees the record and stops using the shard. The agents of the
// shard must be stopped, which saved their homes.
func (s *Shard) release(ctx context.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.lost {
		return ErrLost
	}
	next := s.rec.clone()
	if next.Scratch == nil {
		next.Scratch = map[string]Object{}
	}
	var created []string
	replaced := map[string][2]*snapshots{}
	entries, err := os.ReadDir(filepath.Join(s.dir, "scratch"))
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	for _, e := range entries {
		contextID := e.Name()
		prev, err := s.snapshotsLocked(ctx, contextID)
		if err != nil {
			return err
		}
		cs := s.store(contextID)
		res, err := cs.snapshot(ctx, s.ScratchDir(contextID), prev.scratch, chunks(prev.home, prev.scratch), s.limit)
		var obj Object
		if err == nil {
			obj, err = cs.putManifest(ctx, s.manifestName(contextID, "scratch"), res.manifest)
		}
		if err != nil {
			log.Warn(ctx, "scratch not saved, it is lost", "shard", s.ID, "context", contextID, "cause", err)
			continue
		}
		next.Scratch[contextID] = obj
		created = append(created, obj.Name)
		replaced[contextID] = [2]*snapshots{prev, {home: prev.home, scratch: res.manifest}}
	}
	sessions, err := s.putSessions(ctx)
	if err != nil {
		s.deleteObjects(ctx, created)
		return err
	}
	next.Sessions = sessions
	created = append(created, sessions.Name)
	next.Owner, next.Incarnation = "", ""
	if err := s.commitLocked(ctx, next, created); err != nil {
		return err
	}
	for contextID, r := range replaced {
		s.replaceSnapshotsLocked(ctx, contextID, r[0], r[1])
	}
	s.lost = true
	return nil
}

// commitLocked swaps the record for next. On failure the shard is lost and
// the created objects are deleted; on success the objects next no longer
// lists are deleted.
func (s *Shard) commitLocked(ctx context.Context, next Record, created []string) error {
	rev, err := s.table.swap(ctx, s.ID, next, s.rev)
	if err != nil {
		s.lost = true
		s.deleteObjects(ctx, created)
		return fmt.Errorf("%w: %w", ErrLost, err)
	}
	old := superseded(s.rec, next)
	s.rec, s.rev = next, rev
	s.deleteObjects(ctx, old)
	return nil
}

func superseded(old, next Record) []string {
	listed := map[string]bool{next.Sessions.Name: true}
	for _, o := range next.Homes {
		listed[o.Name] = true
	}
	for _, o := range next.Scratch {
		listed[o.Name] = true
	}
	var names []string
	add := func(o Object) {
		if o.Name != "" && !listed[o.Name] {
			names = append(names, o.Name)
		}
	}
	add(old.Sessions)
	for _, o := range old.Homes {
		add(o)
	}
	for _, o := range old.Scratch {
		add(o)
	}
	return names
}

func (s *Shard) objectName(label string) string {
	s.seq++
	return fmt.Sprintf("%s/e%d-%d-%s", key(s.ID), s.rec.Epoch, s.seq, label)
}

func (s *Shard) manifestName(contextID, label string) string {
	s.seq++
	return fmt.Sprintf("%se%d-%d-%s.json.zst", s.store(contextID).prefix, s.rec.Epoch, s.seq, label)
}

// sweep deletes the shard's objects in names that its record doesn't
// reference: chunks of conversations that expired, and uploads of a server
// that crashed or lost the shard before it committed them.
func (s *Shard) sweep(ctx context.Context, names []string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	keep := map[string]bool{s.rec.Sessions.Name: true}
	conversations := map[string]bool{}
	for c := range s.rec.Homes {
		conversations[c] = true
	}
	for c := range s.rec.Scratch {
		conversations[c] = true
	}
	for c := range conversations {
		snaps, err := s.snapshotsLocked(ctx, c)
		if err != nil {
			return err
		}
		cs := s.store(c)
		keep[s.rec.Homes[c].Name], keep[s.rec.Scratch[c].Name] = true, true
		for hash := range chunks(snaps.home, snaps.scratch) {
			keep[cs.chunkName(hash)] = true
		}
	}
	var unused []string
	for _, name := range names {
		if strings.HasPrefix(name, key(s.ID)+"/") && !keep[name] {
			unused = append(unused, name)
		}
	}
	if len(unused) > 0 {
		log.Info(ctx, "deleting unused snapshot objects", "shard", s.ID, "objects", len(unused))
	}
	s.deleteObjects(ctx, unused)
	return nil
}

func (s *Shard) putSessions(ctx context.Context) (Object, error) {
	tmp := filepath.Join(s.dir, fmt.Sprintf("sessions-%d.snapshot", time.Now().UnixNano()))
	if _, err := s.db.ExecContext(ctx, `VACUUM INTO ?`, tmp); err != nil {
		return Object{}, fmt.Errorf("copying the session map: %w", err)
	}
	data, err := os.ReadFile(tmp)
	if err = errors.Join(err, os.Remove(tmp)); err != nil {
		return Object{}, err
	}
	return s.put(ctx, s.objectName("sessions.db"), data)
}

func (s *Shard) put(ctx context.Context, name string, data []byte) (Object, error) {
	info, err := s.table.obj.PutBytes(ctx, name, data)
	if err != nil {
		return Object{}, fmt.Errorf("uploading %s: %w", name, err)
	}
	return Object{Name: name, Size: int64(info.Size), Saved: time.Now()}, nil
}

func (s *Shard) deleteObjects(ctx context.Context, names []string) {
	for _, name := range names {
		if err := s.table.obj.Delete(ctx, name); err != nil && !errors.Is(err, jetstream.ErrObjectNotFound) {
			log.Warn(ctx, "deleting a snapshot failed", "object", name, "cause", err)
		}
	}
}

// open prepares the local directory and the session map of a shard just claimed.
func (s *Shard) open(ctx context.Context) error {
	if err := os.RemoveAll(s.dir); err != nil {
		return err
	}
	if err := os.MkdirAll(s.dir, 0o700); err != nil {
		return err
	}
	path := filepath.Join(s.dir, "sessions.db")
	if s.rec.Sessions.Name != "" {
		data, err := s.table.obj.GetBytes(ctx, s.rec.Sessions.Name)
		switch {
		case errors.Is(err, jetstream.ErrObjectNotFound):
			log.Warn(ctx, "session map snapshot expired, starting empty", "shard", s.ID)
		case err != nil:
			return fmt.Errorf("downloading the session map: %w", err)
		default:
			if err := os.WriteFile(path, data, 0o600); err != nil {
				return err
			}
		}
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return err
	}
	db.SetMaxOpenConns(1)
	if _, err := db.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS sessions (
		context_id TEXT PRIMARY KEY,
		session_id TEXT NOT NULL,
		agent_key  TEXT NOT NULL,
		updated_at INTEGER NOT NULL
	)`); err != nil {
		return errors.Join(err, db.Close())
	}
	s.db = db
	return nil
}

// close releases the local resources of the shard.
func (s *Shard) close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.lost = true
	var err error
	if s.db != nil {
		err = s.db.Close()
	}
	return errors.Join(err, os.RemoveAll(s.dir))
}

func (s *Shard) isLost() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.lost
}
