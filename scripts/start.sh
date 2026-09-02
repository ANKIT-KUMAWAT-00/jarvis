#!/usr/bin/env bash
# JARVIS Startup Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=================================================="
echo "      INITIALIZING JARVIS AUTONOMOUS SYSTEM       "
echo "=================================================="

# Check Python environment
if [ -f "./venv/bin/python" ]; then
    PYTHON_BIN="./venv/bin/python"
    UVICORN_BIN="./venv/bin/uvicorn"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
    UVICORN_BIN="uvicorn"
else
    echo "Error: Python 3 not detected."
    exit 1
fi

# Detect Apple Silicon / macOS
if [[ "$(uname -s)" == "Darwin" ]]; then
    ARCH=$(uname -m)
    echo "Host detected: macOS ($ARCH)"
fi

echo "Launching JARVIS on http://127.0.0.1:8010 ..."
exec "$UVICORN_BIN" backend.main:app --host 127.0.0.1 --port 8010 --reload --reload-include "*.env"

