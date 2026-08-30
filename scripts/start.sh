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
