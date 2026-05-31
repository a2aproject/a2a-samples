#!/bin/bash
# Runner script for ITK Elixir v1.0 Agent
# Usage: ./run.sh --httpPort 10200 --grpcPort 11200
#
# Parses --httpPort and --grpcPort flags and passes them as env vars
# to the Elixir application.

HTTP_PORT=10200
GRPC_PORT=11200

while [[ $# -gt 0 ]]; do
  case $1 in
    --httpPort)
      HTTP_PORT="$2"
      shift 2
      ;;
    --grpcPort)
      GRPC_PORT="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

export ITK_HTTP_PORT="$HTTP_PORT"
export ITK_GRPC_PORT="$GRPC_PORT"

cd "$(dirname "$0")"
exec mix run --no-halt
