package shards

import (
	"bytes"
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
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
	home, scratch := s.HomeDir(contextID), s.ScratchDir(contextID)
	homeSaved := false
	if _, err := os.Stat(home); errors.Is(err, os.ErrNotExist) {
		obj, saved := s.rec.Homes[contextID]
		if err := s.restore(ctx, obj, saved, home); err != nil {
			return false, err
		}
		homeSaved = saved
	}
	if _, err := os.Stat(scratch); !errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	obj, saved := s.rec.Scratch[contextID]
	if err := s.restore(ctx, obj, saved, scratch); err != nil {
		return false, err
	}
	return homeSaved && !saved, nil
}

func (s *Shard) restore(ctx context.Context, obj Object, saved bool, dir string) error {
	if !saved {
		return os.MkdirAll(dir, 0o700)
	}
	r, err := s.table.obj.Get(ctx, obj.Name)
	if errors.Is(err, jetstream.ErrObjectNotFound) {
		log.Warn(ctx, "snapshot expired, starting empty", "object", obj.Name)
		return os.MkdirAll(dir, 0o700)
	}
	if err != nil {
		return fmt.Errorf("downloading %s: %w", obj.Name, err)
	}
	return errors.Join(unpack(r, dir), r.Close())
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

// Save uploads snapshots of the conversation's agent home, its scratch
// directory if it is within the scratch limit, and the session map. It
// reports whether it saved the scratch directory; a larger one moves only
// with a graceful release.
func (s *Shard) Save(ctx context.Context, contextID string) (scratchSaved bool, err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.lost {
		return false, ErrLost
	}
	next := s.rec.clone()
	if next.Homes == nil {
		next.Homes = map[string]Object{}
	}
	if next.Scratch == nil {
		next.Scratch = map[string]Object{}
	}
	var created []string
	home, err := s.putDir(ctx, s.HomeDir(contextID), "home-"+contextID, s.limit)
	if err != nil {
		return false, err
	}
	next.Homes[contextID] = home
	created = append(created, home.Name)
	scratch, err := s.putDir(ctx, s.ScratchDir(contextID), "scratch-"+contextID, s.scratchLimit)
	switch {
	case errors.Is(err, errTooLarge):
		delete(next.Scratch, contextID)
	case err != nil:
		s.deleteObjects(ctx, created)
		return false, err
	default:
		next.Scratch[contextID] = scratch
		created = append(created, scratch.Name)
		scratchSaved = true
	}
	sessions, err := s.putSessions(ctx)
	if err != nil {
		s.deleteObjects(ctx, created)
		return false, err
	}
	next.Sessions = sessions
	created = append(created, sessions.Name)
	return scratchSaved, s.commitLocked(ctx, next, created)
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
	entries, err := os.ReadDir(filepath.Join(s.dir, "scratch"))
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	for _, e := range entries {
		obj, err := s.putDir(ctx, s.ScratchDir(e.Name()), "scratch-"+e.Name(), s.limit)
		if err != nil {
			log.Warn(ctx, "scratch not saved, it is lost", "shard", s.ID, "context", e.Name(), "cause", err)
			continue
		}
		next.Scratch[e.Name()] = obj
		created = append(created, obj.Name)
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

func (s *Shard) putDir(ctx context.Context, dir, label string, limit int64) (Object, error) {
	var buf bytes.Buffer
	if err := pack(dir, &buf, limit); err != nil {
		return Object{}, fmt.Errorf("packing %s: %w", dir, err)
	}
	return s.put(ctx, s.objectName(label+".tgz"), buf.Bytes())
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
