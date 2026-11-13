module github.com/a2aproject/a2a-samples/samples/go/integrations/mysql

go 1.25.0

require (
	github.com/a2aproject/a2a-go/v2 v2.3.2-0.20260606182037-3134e71be608
	github.com/a2aproject/a2a-samples/samples/go/integrations/nats v0.0.0
	github.com/go-sql-driver/mysql v1.10.0
	github.com/nats-io/nats.go v1.52.0
	golang.org/x/sync v0.20.0
)

require (
	filippo.io/edwards25519 v1.2.0 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/klauspost/compress v1.18.5 // indirect
	github.com/nats-io/nkeys v0.4.15 // indirect
	github.com/nats-io/nuid v1.0.1 // indirect
	golang.org/x/crypto v0.52.0 // indirect
	golang.org/x/sys v0.45.0 // indirect
)

replace github.com/a2aproject/a2a-samples/samples/go/integrations/nats => ../nats
