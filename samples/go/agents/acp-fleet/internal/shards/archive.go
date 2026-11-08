package shards

import (
	"archive/tar"
	"compress/gzip"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"slices"
)

// skipped are directories of caches that agents and tools write to their
// home, which are large and can be rebuilt.
var skipped = []string{".cache", ".npm", "node_modules"}

var errTooLarge = errors.New("archive is larger than the limit")

type limitWriter struct {
	w    io.Writer
	left int64
}

func (l *limitWriter) Write(p []byte) (int, error) {
	if int64(len(p)) > l.left {
		return 0, errTooLarge
	}
	l.left -= int64(len(p))
	return l.w.Write(p)
}

// pack writes dir as a gzipped tar to w, failing once it exceeds limit bytes.
// Symbolic links and the skipped directories are left out.
func pack(dir string, w io.Writer, limit int64) error {
	gz := gzip.NewWriter(&limitWriter{w: w, left: limit})
	tw := tar.NewWriter(gz)
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
		hdr, err := tar.FileInfoHeader(info, "")
		if err != nil {
			return err
		}
		hdr.Name = filepath.ToSlash(rel)
		if err := tw.WriteHeader(hdr); err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		f, err := os.Open(path)
		if err != nil {
			return err
		}
		_, err = io.Copy(tw, f)
		return errors.Join(err, f.Close())
	})
	return errors.Join(err, tw.Close(), gz.Close())
}

// unpack extracts a gzipped tar into dir. Entries can't leave dir.
func unpack(r io.Reader, dir string) error {
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return err
	}
	root, err := os.OpenRoot(dir)
	if err != nil {
		return err
	}
	gz, err := gzip.NewReader(r)
	if err != nil {
		return errors.Join(err, root.Close())
	}
	tr := tar.NewReader(gz)
	for {
		hdr, err := tr.Next()
		if errors.Is(err, io.EOF) {
			return errors.Join(gz.Close(), root.Close())
		}
		if err == nil {
			err = extract(root, hdr, tr)
		}
		if err != nil {
			return errors.Join(fmt.Errorf("extracting into %s: %w", dir, err), gz.Close(), root.Close())
		}
	}
}

func extract(root *os.Root, hdr *tar.Header, r io.Reader) error {
	name := filepath.FromSlash(hdr.Name)
	switch hdr.Typeflag {
	case tar.TypeDir:
		return root.MkdirAll(name, 0o700)
	case tar.TypeReg:
		if dir := filepath.Dir(name); dir != "." {
			if err := root.MkdirAll(dir, 0o700); err != nil {
				return err
			}
		}
		f, err := root.OpenFile(name, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o600)
		if err != nil {
			return err
		}
		_, err = io.Copy(f, r)
		return errors.Join(err, f.Close())
	}
	return nil
}
