module github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet

go 1.26.0

require (
	github.com/a2aproject/a2a-go/v2 v2.8.0
	github.com/a2aproject/a2a-samples/samples/go/integrations/mysql v0.0.0-00010101000000-000000000000
	github.com/a2aproject/a2a-samples/samples/go/integrations/nats v0.0.0
	github.com/go-sql-driver/mysql v1.10.1
	github.com/nats-io/nats.go v1.55.0
	modernc.org/sqlite v1.62.0
)

require (
	filippo.io/edwards25519 v1.2.0 // indirect
	github.com/dustin/go-humanize v1.1.0 // indirect
	github.com/google/jsonschema-go v0.4.3 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/klauspost/compress v1.20.0 // indirect
	github.com/mattn/go-isatty v0.0.24 // indirect
	github.com/nats-io/nkeys v0.4.16 // indirect
	github.com/nats-io/nuid v1.0.1 // indirect
	github.com/ncruces/go-strftime v1.1.0 // indirect
	github.com/remyoudompheng/bigfft v0.0.0-20230129092748-24d4a6f8daec // indirect
	golang.org/x/crypto v0.57.0 // indirect
	golang.org/x/mod v0.42.0 // indirect
	golang.org/x/sync v0.24.0 // indirect
	golang.org/x/sys v0.49.0 // indirect
	modernc.org/libc v1.80.1 // indirect
	modernc.org/mathutil v1.7.1 // indirect
	modernc.org/memory v1.12.1 // indirect
)

replace (
	github.com/a2aproject/a2a-samples/samples/go/integrations/mysql => ../../integrations/mysql
	github.com/a2aproject/a2a-samples/samples/go/integrations/nats => ../../integrations/nats
)
