#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/../../.."
PROTO_DIR="$PROJECT_ROOT/protos"
OUT_DIR="$SCRIPT_DIR/pyproto"

# Create output directory
mkdir -p "$OUT_DIR"
touch "$OUT_DIR/__init__.py"

# Compile proto
python3 -m grpc_tools.protoc \
	-I="$PROTO_DIR" \
	--python_out="$OUT_DIR" \
	--grpc_python_out="$OUT_DIR" \
	"$PROTO_DIR/instruction.proto"

# Fix imports in generated file
sed -i 's/^import instruction_pb2 as instruction__pb2/from . import instruction_pb2 as instruction__pb2/' "$OUT_DIR/instruction_pb2_grpc.py"

echo "Protos compiled successfully to $OUT_DIR"
