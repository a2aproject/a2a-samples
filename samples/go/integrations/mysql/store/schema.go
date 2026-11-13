package store

import _ "embed"

// Schema creates the tables of the [Store] and the [Outbox]. Deployments run
// schema.sql when MySQL starts.
//
//go:embed schema.sql
var Schema string
