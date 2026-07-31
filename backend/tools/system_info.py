"""
JARVIS System Environment Discovery Tool
Specialized for macOS Apple Silicon detection, runtime environments, and installed developer tooling.
"""

import os
import platform
import shutil
import subprocess
import time
from typing import Dict, Any
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel


class SystemInfoTool(Tool):
    name: str = "system_info"
    description: str = "Inspect macOS host environment, Apple Silicon architecture, runtimes, and developer tooling."
    permission_level: ActionLevel = ActionLevel.LEVEL_0_READ

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        
        info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.mac_ver()[0] if platform.system() == "Darwin" else platform.version(),
            "architecture": platform.machine(),
            "is_apple_silicon": (platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64")),
            "python_version": platform.python_version(),
            "tools": {}
        }

        # Check installed developer tools
        commands_to_check = ["git", "node", "npm", "python3", "docker", "screencapture", "curl", "zsh", "brew"]
        for cmd in commands_to_check:
            path = shutil.which(cmd)
            version_str = None
            if path:
                try:
                    res = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=2.0)
                    if res.returncode == 0:
                        version_str = res.stdout.strip().splitlines()[0]
                except Exception:
                    pass
            info["tools"][cmd] = {
                "installed": path is not None,
                "path": path,
                "version": version_str
            }

        # Add memory and disk estimates if on macOS
        try:
            statvfs = os.statvfs("/")
            free_gb = round((statvfs.f_bavail * statvfs.f_frsize) / (1024 ** 3), 1)
            total_gb = round((statvfs.f_blocks * statvfs.f_frsize) / (1024 ** 3), 1)
            info["disk_storage"] = {
                "free_gb": free_gb,
                "total_gb": total_gb,
                "used_percent": round(((total_gb - free_gb) / total_gb) * 100, 1)
            }
        except Exception:
            pass

        return ToolResult(
            success=True,
            output=info,
            raw_data=info,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        if result.success and result.raw_data and "architecture" in result.raw_data:
            return VerificationResult(
                verified=True,
                expected="System info dictionary",
                actual=f"{result.raw_data.get('os')} ({result.raw_data.get('architecture')})",
                message="System environment verified."
            )
        return VerificationResult(
            verified=False,
            expected="System info dictionary",
            actual="Failed to collect system info",
            message="System info verification failed."
        )
