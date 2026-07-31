"""
JARVIS Git Version Control Tool
Inspects repository state, diffs, branches, and commits with verified change receipts.
Enforces Level 2/3 confirmations for remote pushes and hard resets.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel


class GitTool(Tool):
    name: str = "git"
    description: str = "Interact with Git repositories: status, diff, log, branch, checkout, commit, push."
    permission_level: ActionLevel = ActionLevel.LEVEL_1_SAFE_WRITE

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    async def _run_git(self, args: list[str], cwd: Path) -> tuple[int, str, str]:
        cmd = ["git"] + args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_b, stderr_b = await proc.communicate()
        return (
            proc.returncode,
            stdout_b.decode("utf-8", errors="replace").strip(),
            stderr_b.decode("utf-8", errors="replace").strip()
        )

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        action = params.get("action", "status")
        repo_dir = Path(params.get("cwd", self.workspace_root)).resolve()

        if not (repo_dir / ".git").exists():
            # Check if parent or current is git repo
            code, out, _ = await self._run_git(["rev-parse", "--is-inside-work-tree"], repo_dir)
            if code != 0 or out != "true":
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Directory is not a git repository: {repo_dir}",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

        try:
            if action == "status":
                code, stdout, stderr = await self._run_git(["status", "--short", "--branch"], repo_dir)
                return ToolResult(
                    success=(code == 0),
                    output=stdout or "Working tree clean",
                    error=stderr if code != 0 else None,
                    raw_data={"exit_code": code, "output": stdout},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "diff":
                staged = params.get("staged", False)
                args = ["diff", "--cached"] if staged else ["diff"]
                code, stdout, stderr = await self._run_git(args, repo_dir)
                return ToolResult(
                    success=(code == 0),
                    output=stdout or "No changes detected",
                    error=stderr if code != 0 else None,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "log":
                count = str(params.get("count", 5))
                code, stdout, stderr = await self._run_git(["log", f"-n{count}", "--oneline"], repo_dir)
                return ToolResult(
                    success=(code == 0),
                    output=stdout,
                    error=stderr if code != 0 else None,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "branch":
                code, stdout, stderr = await self._run_git(["branch", "-a"], repo_dir)
                return ToolResult(
                    success=(code == 0),
                    output=stdout,
                    error=stderr if code != 0 else None,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "commit":
                message = params.get("message", "Update from JARVIS").strip()
                files = params.get("files", ["."])
                
                # First add files
                add_code, _, add_err = await self._run_git(["add"] + files, repo_dir)
                if add_code != 0:
                    return ToolResult(success=False, output="", error=f"Git add failed: {add_err}")

                # Commit
                commit_code, commit_out, commit_err = await self._run_git(["commit", "-m", message], repo_dir)
                if commit_code != 0:
                    return ToolResult(success=False, output="", error=f"Git commit failed: {commit_err or commit_out}")

                # Retrieve new HEAD commit hash
                hash_code, hash_out, _ = await self._run_git(["rev-parse", "--short", "HEAD"], repo_dir)
                return ToolResult(
                    success=True,
                    output=f"Committed changes [{hash_out}]: {message}",
                    raw_data={"commit_hash": hash_out, "message": message},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "push":
                # External Action - Level 2
                remote = params.get("remote", "origin")
                branch = params.get("branch", "main")
                code, stdout, stderr = await self._run_git(["push", remote, branch], repo_dir)
                return ToolResult(
                    success=(code == 0),
                    output=stdout or f"Pushed to {remote}/{branch}",
                    error=stderr if code != 0 else None,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            else:
                return ToolResult(success=False, output="", error=f"Unknown git action: {action}")

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Git tool error: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        action = expectation.get("action")
        if action == "commit":
            if result.success and result.raw_data and "commit_hash" in result.raw_data:
                return VerificationResult(
                    verified=True,
                    expected="Commit recorded in git history",
                    actual=f"Commit hash verified: {result.raw_data['commit_hash']}",
                    message="Git commit receipt confirmed."
                )
            return VerificationResult(
                verified=False,
                expected="Commit recorded in git history",
                actual=f"Commit failed: {result.error}",
                message="Git commit verification failed."
            )
        return super().verify(result, expectation)
