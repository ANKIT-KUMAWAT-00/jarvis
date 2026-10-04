"""
JARVIS Process Management Tool
Starts, inspects, monitors, checks health, and stops background processes.
"""

import asyncio
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel


class ManagedProcess:
    def __init__(self, name: str, command: str, process: subprocess.Popen, log_file: Path):
        self.name = name
        self.command = command
        self.process = process
        self.log_file = log_file
        self.started_at = time.time()

    def is_alive(self) -> bool:
        return self.process.poll() is None

    def get_logs(self, max_lines: int = 50) -> str:
        if self.log_file.exists():
            lines = self.log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-max_lines:])
        return ""


class ProcessTool(Tool):
    name: str = "process"
    description: str = "Start, inspect, stop, restart, and health-check background processes."
    permission_level: ActionLevel = ActionLevel.LEVEL_1_SAFE_WRITE

    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.managed_processes: Dict[str, ManagedProcess] = {}

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        action = params.get("action", "inspect")
        name = params.get("name", "").strip()

        try:
            if action == "start":
                command = params.get("command", "").strip()
                cwd = params.get("cwd", ".")
                if not name or not command:
                    return ToolResult(success=False, output="", error="Name and command are required to start a process.")

                # If already running with this name, stop it first
                if name in self.managed_processes and self.managed_processes[name].is_alive():
                    self.managed_processes[name].process.terminate()
                    await asyncio.sleep(0.5)

                log_file = self.logs_dir / f"proc_{name}.log"
                f_out = open(log_file, "w", encoding="utf-8")
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd,
                    stdout=f_out,
                    stderr=subprocess.STDOUT
                )

                managed = ManagedProcess(name=name, command=command, process=proc, log_file=log_file)
                self.managed_processes[name] = managed

                # Short delay to detect early crashes
                await asyncio.sleep(0.8)
                alive = managed.is_alive()

                if not alive:
                    exit_code = proc.poll()
                    logs = managed.get_logs()
                    return ToolResult(
                        success=False,
                        output=f"Process '{name}' crashed immediately with exit code {exit_code}.\nLogs:\n{logs}",
                        error=f"Process exited prematurely with code {exit_code}",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )

                return ToolResult(
                    success=True,
                    output=f"Process '{name}' started (PID: {proc.pid}). Output logged to {log_file.name}.",
                    raw_data={"pid": proc.pid, "name": name, "alive": True},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "inspect":
                if name:
                    if name not in self.managed_processes:
                        return ToolResult(success=False, output="", error=f"Process '{name}' not found.")
                    p = self.managed_processes[name]
                    alive = p.is_alive()
                    logs = p.get_logs(max_lines=20)
                    return ToolResult(
                        success=True,
                        output={
                            "name": p.name,
                            "command": p.command,
                            "pid": p.process.pid,
                            "alive": alive,
                            "uptime_seconds": int(time.time() - p.started_at),
                            "recent_logs": logs
                        },
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                else:
                    # List all
                    results = []
                    for p_name, p in list(self.managed_processes.items()):
                        results.append({
                            "name": p.name,
                            "command": p.command,
                            "pid": p.process.pid,
                            "alive": p.is_alive(),
                            "uptime_seconds": int(time.time() - p.started_at)
                        })
                    return ToolResult(
                        success=True,
                        output=results,
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )

            elif action == "stop":
                if name not in self.managed_processes:
                    return ToolResult(success=False, output="", error=f"Process '{name}' not found.")
                p = self.managed_processes[name]
                if p.is_alive():
                    p.process.terminate()
                    try:
                        p.process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        p.process.kill()
                    return ToolResult(
                        success=True,
                        output=f"Process '{name}' stopped cleanly.",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                return ToolResult(
                    success=True,
                    output=f"Process '{name}' was already stopped.",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "health_check":
                url = params.get("url", "http://127.0.0.1:8000/health")
                try:
                    resp = requests.get(url, timeout=3.0)
                    return ToolResult(
                        success=(resp.status_code < 400),
                        output=f"Health check to {url} returned HTTP {resp.status_code}: {resp.text[:200]}",
                        raw_data={"status_code": resp.status_code, "body": resp.text[:500]},
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                except Exception as e:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Health check failed to {url}: {str(e)}",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )

            else:
                return ToolResult(success=False, output="", error=f"Unknown process action: {action}")

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Process management error: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        action = expectation.get("action")
        name = expectation.get("name")
        if action == "start":
            proc = self.managed_processes.get(name)
            if proc and proc.is_alive():
                return VerificationResult(
                    verified=True,
                    expected=f"Process '{name}' is running",
                    actual=f"Process alive with PID {proc.process.pid}",
                    message="Process start verified."
                )
            return VerificationResult(
                verified=False,
                expected=f"Process '{name}' running",
                actual="Process is dead or failed to start",
                message="Process start verification failed."
            )
        return super().verify(result, expectation)
