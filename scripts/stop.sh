#!/usr/bin/env bash
# JARVIS Stop Script
echo "Stopping any running JARVIS instances on port 8010..."

PID=$(lsof -ti :8010 || true)
if [ -n "$PID" ]; then
