"""
JARVIS Screen Vision Tool
Captures macOS screen frames dynamically using native screencapture utility,
encodes to base64 for Gemini Vision multimodal analysis.
Never relies on stale cached frames.
"""

import asyncio
import base64
import time
from pathlib import Path
from typing import Dict, Any, Optional
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel


class ScreenVisionTool(Tool):
    name: str = "screen"
    description: str = "Capture live macOS display frame and prepare for visual multimodal analysis."
    permission_level: ActionLevel = ActionLevel.LEVEL_0_READ

    def __init__(self, scratch_dir: Path):
        self.scratch_dir = scratch_dir
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        capture_path = self.scratch_dir / f"screen_live_{int(start_time)}.png"
        
        # Use macOS native screencapture tool
        # -x: mute sound
        # -C: capture cursor
        # -t png: PNG format
        cmd = ["/usr/sbin/screencapture", "-x", "-C", "-t", "png", str(capture_path)]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr_b = await proc.communicate()

            if proc.returncode != 0:
                err_msg = stderr_b.decode("utf-8", errors="replace")
                return ToolResult(
                    success=False,
                    output="",
                    error=f"screencapture utility failed: {err_msg}. Note: Screen Recording permission may be required in macOS System Settings.",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            if not capture_path.exists() or capture_path.stat().st_size == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error="Screen capture resulted in 0-byte file. Check macOS Privacy & Security > Screen Recording permissions.",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )

            # Read and encode to base64
            image_bytes = capture_path.read_bytes()
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            file_size_kb = len(image_bytes) // 1024

            # Clean up old captures, keeping only current
            for p in self.scratch_dir.glob("screen_live_*.png"):
                if p != capture_path:
                    try:
                        p.unlink()
                    except Exception:
                        pass

            return ToolResult(
                success=True,
                output=f"Live screen captured successfully ({file_size_kb} KB, captured at {time.strftime('%H:%M:%S')}).",
                raw_data={
                    "base64_image": b64_image,
                    "mime_type": "image/png",
                    "file_path": str(capture_path),
                    "timestamp": time.time(),
                    "size_kb": file_size_kb
                },
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Screen capture error: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        if result.success and result.raw_data and "base64_image" in result.raw_data:
            return VerificationResult(
                verified=True,
                expected="Live screen frame captured as base64",
                actual=f"Frame verified ({result.raw_data.get('size_kb')} KB)",
                message="Screen capture receipt verified."
            )
        return VerificationResult(
            verified=False,
            expected="Live screen frame captured",
            actual=f"Capture failed: {result.error}",
            message="Screen capture verification failed."
        )
