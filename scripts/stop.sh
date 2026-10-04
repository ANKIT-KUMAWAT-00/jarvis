#!/usr/bin/env bash
# JARVIS Stop Script
echo "Stopping any running JARVIS instances on port 8010..."

PID=$(lsof -ti :8010 || true)
if [ -n "$PID" ]; then
    echo "Terminating process PID(s): $PID"
    kill -15 $PID 2>/dev/null || kill -9 $PID 2>/dev/null

    echo "JARVIS stopped successfully."
else
    echo "No JARVIS instance detected on port 8010."
fi
