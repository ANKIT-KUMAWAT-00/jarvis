#!/usr/bin/env bash
# JARVIS Preflight Verification Runner
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

if [ -f "./venv/bin/python" ]; then
    PYTHON_BIN="./venv/bin/python"
else
    PYTHON_BIN="python3"
fi

exec "$PYTHON_BIN" preflight.py "$@"
