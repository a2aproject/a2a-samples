#!/bin/bash

# Setup script for Hello World Azure AI Foundry Agent

set -e

echo "🚀 Setting up Hello World Azure AI Foundry Agent..."

# Check if Python 3.11+ is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version is compatible (>= 3.11)"
else
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi

# Check if uv is installed, if not suggest pip
if command -v uv &> /dev/null; then
    echo "📦 Installing dependencies with uv..."
    uv sync
    echo "✅ Dependencies installed with uv"
else
    echo "📦 uv not found, using pip..."
    python3 -m pip install -e .
    echo "✅ Dependencies installed with pip"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Please edit .env file with your Azure AI Foundry credentials"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Azure AI Foundry credentials"
echo "2. Run the agent: python -m hello_world_agent"
echo "3. Or run interactive client: python client.py"
echo ""
