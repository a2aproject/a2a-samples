#!/bin/bash

# Script to build Go proto library from .proto files
# Required dependencies: protoc, protoc-gen-go

# Ensure we are in the go directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "Compiling protos from ../../../protos into pb/..."

# Create pb directory if it doesn't exist
mkdir -p pb

# Run protoc
# -I../../../protos: look for imports in the protos directory
# --go_out=pb: output generated files into the pb directory
# --go_opt=Minstruction.proto=itk/agents/go/v10/pb: map instruction.proto to the local pb package
# --go_opt=paths=source_relative: use relative paths for output
protoc --proto_path=../../../protos \
	--go_out=pb \
	--go_opt=Minstruction.proto=itk/agents/go/v10/pb \
	--go_opt=paths=source_relative \
	../../../protos/instruction.proto

echo "Done. Generated files are in pb/"
