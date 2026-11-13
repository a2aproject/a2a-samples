// Package mysqltest connects integration tests to a MySQL server, such as the
// one in this module's compose.yaml.
package mysqltest

import (
	"database/sql"
	"strings"
	"testing"
	"time"

	"github.com/a2aproject/a2a-samples/samples/go/integrations/mysql/store"
	_ "github.com/go-sql-driver/mysql" // MySQL driver registration
)

// DSN is the MySQL connection string used by integration tests.
const DSN = "root:root@tcp(localhost:3306)/planner?parseTime=true"

// Open connects to [DSN], retrying for up to 30 seconds while the server
// starts, and recreates the tables of [store.Schema].
func Open(t testing.TB) *sql.DB {
	t.Helper()
	db, err := sql.Open("mysql", DSN)
	if err != nil {
		t.Fatalf("sql.Open() error = %v", err)
	}
	t.Cleanup(func() {
		if err := db.Close(); err != nil {
			t.Errorf("db.Close() error = %v", err)
		}
	})
	for deadline := time.Now().Add(30 * time.Second); time.Now().Before(deadline); time.Sleep(500 * time.Millisecond) {
		if err = db.Ping(); err == nil {
			break
		}
	}
	if err != nil {
		t.Fatalf("db.Ping() error = %v", err)
	}

	stmts := []string{"DROP TABLE IF EXISTS `outbox`", "DROP TABLE IF EXISTS `tasks`"}
	for _, stmt := range strings.Split(store.Schema, ";") {
		if stmt = strings.TrimSpace(stmt); stmt != "" {
			stmts = append(stmts, stmt)
		}
	}
	for _, stmt := range stmts {
		if _, err := db.Exec(stmt); err != nil {
			t.Fatalf("db.Exec(%q) error = %v", stmt, err)
		}
	}
	return db
}
