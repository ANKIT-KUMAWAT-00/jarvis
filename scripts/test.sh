#!/usr/bin/env bash
# JARVIS Test Suite Runner
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "Running full JARVIS test suite..."
if [ -f "./venv/bin/pytest" ]; then
    PYTEST_BIN="./venv/bin/pytest"
else
    PYTEST_BIN="pytest"
fi

exec "$PYTEST_BIN" -v "$@"
