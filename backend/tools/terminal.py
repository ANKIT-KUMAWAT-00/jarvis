"""
JARVIS Terminal Tool
Controlled asynchronous shell execution with strict timeout, output capture,
secret masking, and exit status verification.
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel
from backend.security.sanitizer import Sanitizer


class TerminalTool(Tool):
    name: str = "terminal"
    description: str = "Execute controlled shell commands with timeout, captured stdout/stderr, and exit code verification."
    permission_level: ActionLevel = ActionLevel.LEVEL_1_SAFE_WRITE

    def __init__(self, default_cwd: Path):
        self.default_cwd = default_cwd

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        command = params.get("command", "").strip()
        cwd_param = params.get("cwd")
        timeout_seconds = float(params.get("timeout", self.timeout_seconds))

        if not command:
            return ToolResult(
                success=False,
                output="",
                error="No command provided to terminal tool.",
                execution_time_ms=0
            )

        # Inspect if command is destructive
        is_destructive, danger_reason = Sanitizer.is_destructive_command(command)
        if is_destructive and not params.get("authorized_high_risk", False):
            return ToolResult(
                success=False,
                output="",
                error=f"Security Intercept: {danger_reason} (Action Level 3 confirmation required)",
                execution_time_ms=0
            )

        cwd = Path(cwd_param).resolve() if cwd_param else self.default_cwd
        if not cwd.exists():
            cwd = self.default_cwd

        env = os.environ.copy()
        env["PAGER"] = "cat"
        env["TERM"] = "dumb"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout_seconds}s: '{command}'",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
            exit_code = process.returncode

            # Mask secrets in captured terminal output
            masked_stdout = Sanitizer.mask_secrets(stdout)
            masked_stderr = Sanitizer.mask_secrets(stderr)

            combined_output = masked_stdout
            if masked_stderr:
                combined_output = f"{masked_stdout}\n[STDERR]:\n{masked_stderr}" if masked_stdout else f"[STDERR]:\n{masked_stderr}"

            success = (exit_code == 0)

            return ToolResult(
                success=success,
                output=combined_output,
                error=None if success else f"Command exited with non-zero code {exit_code}",
                raw_data={
                    "exit_code": exit_code,
                    "stdout": masked_stdout,
                    "stderr": masked_stderr,
                    "command": command
                },
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Subprocess execution error: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        expected_exit_code = expectation.get("expected_exit_code", 0)
        expected_output_substring = expectation.get("output_contains")

        actual_exit_code = result.raw_data.get("exit_code") if result.raw_data else None

        if actual_exit_code != expected_exit_code:
            return VerificationResult(
                verified=False,
                expected=f"Exit code {expected_exit_code}",
                actual=f"Exit code {actual_exit_code}",
                message=f"Terminal verification failed: process returned code {actual_exit_code}."
            )

        if expected_output_substring:
            output_str = str(result.output or "")
            if expected_output_substring not in output_str:
                return VerificationResult(
                    verified=False,
                    expected=f"Output containing '{expected_output_substring}'",
                    actual="Substring not found in terminal output",
                    message="Terminal verification failed: expected output content was missing."
                )

        return VerificationResult(
            verified=True,
            expected=f"Exit code {expected_exit_code}",
            actual=f"Exit code {actual_exit_code}",
            message="Terminal execution verified cleanly."
        )
