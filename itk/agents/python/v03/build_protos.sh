#!/bin/bash

# Script to build Python proto library from .proto files
# Required dependencies: grpcio-tools

# Ensure we are in the v03 directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "Compiling protos from ../../../protos into pyproto/..."

# Create pyproto directory if it doesn't exist
mkdir -p pyproto

# Run protoc via grpc_tools using uv
# -I../../../protos: look for imports in the protos directory
# --python_out=pyproto: output generated files into the pyproto directory
# --grpc_python_out=pyproto: output generated gRPC files into the pyproto directory
uv run python -m grpc_tools.protoc --proto_path=../../../protos \
	--python_out=pyproto \
	--grpc_python_out=pyproto \
	../../../protos/instruction.proto

# Fix imports in generated gRPC file for local module usage
# (Standard protoc-gen-grpc-python behavior requires this for relative packages)
sed -i 's/import instruction_pb2 as instruction__pb2/from . import instruction_pb2 as instruction__pb2/' pyproto/instruction_pb2_grpc.py

echo "Done. Generated files are in pyproto/"
