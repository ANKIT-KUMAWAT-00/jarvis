"""
JARVIS Filesystem Tool
Enforces workspace boundaries, safe modifications, and path traversal protection.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel
from backend.security.sanitizer import Sanitizer


class FilesystemTool(Tool):
    name: str = "filesystem"
    description: str = "Perform secure filesystem operations (read, write, modify, list, search, info)."
    permission_level: ActionLevel = ActionLevel.LEVEL_1_SAFE_WRITE

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        action = params.get("action", "read_file")
        target = params.get("path", "")

        # Boundary check
        is_safe, resolved_path, reason = Sanitizer.validate_path(target, self.workspace_root)
        if not is_safe:
            return ToolResult(
                success=False,
                output="",
                error=f"Security Boundary Error: {reason}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        try:
            if action == "list_dir":
                if not resolved_path.exists():
                    return ToolResult(success=False, output="", error=f"Directory does not exist: {resolved_path}")
                items = []
                for entry in sorted(resolved_path.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
                    items.append({
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size_bytes": entry.stat().st_size if entry.is_file() else None
                    })
                return ToolResult(
                    success=True,
                    output=items,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "read_file":
                if not resolved_path.is_file():
                    return ToolResult(success=False, output="", error=f"File not found: {resolved_path}")
                content = resolved_path.read_text(encoding="utf-8", errors="replace")
                sanitized_content = Sanitizer.mask_secrets(content)
                return ToolResult(
                    success=True,
                    output=sanitized_content,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "write_file":
                content = params.get("content", "")
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                resolved_path.write_text(content, encoding="utf-8")
                return ToolResult(
                    success=True,
                    output=f"Successfully wrote {len(content)} bytes to {resolved_path.name}",
                    raw_data={"path": str(resolved_path), "bytes": len(content)},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "modify_file":
                if not resolved_path.is_file():
                    return ToolResult(success=False, output="", error=f"Target file does not exist: {resolved_path}")
                target_str = params.get("target_string", "")
                replacement_str = params.get("replacement_string", "")
                content = resolved_path.read_text(encoding="utf-8")
                if target_str not in content:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Target string to replace was not found in {resolved_path.name}"
                    )
                new_content = content.replace(target_str, replacement_str, 1)
                resolved_path.write_text(new_content, encoding="utf-8")
                return ToolResult(
                    success=True,
                    output=f"Successfully modified {resolved_path.name}",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "file_info":
                if not resolved_path.exists():
                    return ToolResult(success=False, output="", error=f"Path does not exist: {resolved_path}")
                stat = resolved_path.stat()
                return ToolResult(
                    success=True,
                    output={
                        "path": str(resolved_path),
                        "size_bytes": stat.st_size,
                        "is_dir": resolved_path.is_dir(),
                        "is_file": resolved_path.is_file(),
                        "modified_at": stat.st_mtime
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "search_files":
                query = params.get("query", "").lower()
                matches = []
                for p in resolved_path.rglob("*"):
                    if p.is_file() and query in p.name.lower():
                        matches.append(str(p.relative_to(self.workspace_root)))
                        if len(matches) >= 50:
                            break
                return ToolResult(
                    success=True,
                    output=matches,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            elif action == "delete_file":
                # Level 3 operation
                if not resolved_path.exists():
                    return ToolResult(success=False, output="", error=f"Path does not exist: {resolved_path}")
                if resolved_path.is_dir():
                    import shutil
                    shutil.rmtree(resolved_path)
                else:
                    resolved_path.unlink()
                return ToolResult(
                    success=True,
                    output=f"Successfully deleted {resolved_path.name}",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            else:
                return ToolResult(success=False, output="", error=f"Unknown filesystem action: {action}")

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Filesystem error: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        action = expectation.get("action")
        target_path = expectation.get("path")
        
        if not result.success:
            return VerificationResult(
                verified=False,
                expected=f"Successful execution of {action}",
                actual=f"Error: {result.error}",
                message="Filesystem action failed."
            )

        if action == "write_file":
            p = Path(target_path)
            if not p.is_absolute():
                p = self.workspace_root / p
            if p.exists() and p.is_file() and p.stat().st_size > 0:
                return VerificationResult(
                    verified=True,
                    expected=f"File {p.name} exists with non-zero size",
                    actual=f"File verified on disk ({p.stat().st_size} bytes)",
                    message="Verification succeeded."
                )
            else:
                return VerificationResult(
                    verified=False,
                    expected=f"File {p.name} created on disk",
                    actual="File does not exist or has 0 bytes",
                    message="Verification failed: file missing or empty."
                )

        if action == "delete_file":
            p = Path(target_path)
            if not p.is_absolute():
                p = self.workspace_root / p
            if not p.exists():
                return VerificationResult(
                    verified=True,
                    expected=f"File {p.name} deleted",
                    actual="Confirmed removed from filesystem",
                    message="Verification succeeded."
                )
            return VerificationResult(
                verified=False,
                expected=f"File {p.name} deleted",
                actual="File still exists on disk",
                message="Verification failed: file was not removed."
            )

        return super().verify(result, expectation)
